import asyncio
import logging
import os
import random
import sqlite3
from datetime import datetime
from threading import Lock

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()
router = Router()
dp.include_router(router)

db_lock = Lock()
conn = sqlite3.connect("nofap.db", check_same_thread=False)
cursor = conn.cursor()

with db_lock:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER,
        chat_id INTEGER,
        start_time TEXT,
        breaks INTEGER DEFAULT 0,
        starts INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, chat_id)
    )
    """)
    conn.commit()

# -------------------- ФРАЗЫ --------------------
break_messages = [
    "Мне так больно… ты сорвался… пожалуйста… давай начнём заново…",
    "Я не злюсь… я просто очень расстроен… но верю в тебя…",
    "Каждый раз, когда ты срываешься, мне тяжело… прошу, держись…",
    "Ну зачем… ну зачем… ты же держался… давай попробуем снова…"
]

praise_messages = [
    "Я так горжусь тобой… ты даже не представляешь… продолжай держаться…",
    "Ты делаешь невероятную вещь… правда… я рад за тебя…",
    "Ты становишься сильнее с каждым часом… я это чувствую…",
    "Продолжай… пожалуйста… у тебя отлично получается…"
]

alive_messages = [
    "Пожалуйста… кто держится — держитесь дальше…",
    "Я верю, что сегодня никто не сорвётся… держитесь…",
    "Если сейчас тяжело — просто отвлекись… не сдавайся…"
]

# -------------------- ЛОГИКА --------------------
def get_user(user_id, chat_id):
    with db_lock:
        cursor.execute(
            "SELECT * FROM users WHERE user_id=? AND chat_id=?",
            (user_id, chat_id),
        )
        return cursor.fetchone()

def update_user(user_id, chat_id, break_add=False):
    now = datetime.utcnow().isoformat()
    with db_lock:
        user = get_user(user_id, chat_id)
        if user is None:
            cursor.execute("""
            INSERT INTO users (user_id, chat_id, start_time, breaks, starts)
            VALUES (?, ?, ?, 0, 1)
            """, (user_id, chat_id, now))
        else:
            breaks = user[3] + (1 if break_add else 0)
            starts = user[4] + 1
            cursor.execute("""
            UPDATE users
            SET start_time=?, breaks=?, starts=?
            WHERE user_id=? AND chat_id=?
            """, (now, breaks, starts, user_id, chat_id))
        conn.commit()

def time_stats(start_time):
    start = datetime.fromisoformat(start_time)
    delta = datetime.utcnow() - start
    hours = int(delta.total_seconds() // 3600)
    days = hours // 24
    return days, hours

# -------------------- РАНГИ --------------------
def get_rank(days):
    if days >= 60: return "🏆 Легенда воздержания"
    if days >= 30: return "🛡 Железный дух"
    if days >= 21: return "⚔ Закалённый волей"
    if days >= 14: return "🥋 Боец с искушением"
    if days >= 7: return "🗡 Воин дисциплины"
    if days >= 3: return "🙂 Держится изо всех сил"
    return "🐣 Новичок пути"

# -------------------- ХЭНДЛЕР ВСЕХ СООБЩЕНИЙ --------------------
@router.message()
async def all_messages(message: Message):
    if not message.text:
        return
    text = message.text.lower()

    if text == "нофап старт":
        user = get_user(message.from_user.id, message.chat.id)
        if user is None:
            update_user(message.from_user.id, message.chat.id)
            await message.answer("Твой путь начался… я буду рядом и поддерживать тебя… пожалуйста, держись!")
        else:
            update_user(message.from_user.id, message.chat.id, break_add=True)
            await message.answer(random.choice(break_messages))

    elif text == "мой нофап":
        user = get_user(message.from_user.id, message.chat.id)
        if user is None:
            await message.answer("Ты ещё не начал… напиши «нофап старт»")
            return
        days, hours = time_stats(user[2])
        coef = round(user[3] / user[4], 2)
        await message.answer(f"⏳ Ты держишься {days} дней ({hours} часов)\nСрывов: {user[3]}\nКоэффициент: {coef}\n\n"+random.choice(praise_messages))

    elif text == "топ нофаперов":
        with db_lock:
            cursor.execute("SELECT * FROM users WHERE chat_id=?", (message.chat.id,))
            users = cursor.fetchall()
        rating = []
        for u in users:
            days, hours = time_stats(u[2])
            rating.append((days, hours, u[3]))
        rating.sort(reverse=True, key=lambda x: x[0])
        msg = "🏆 Топ нофаперов:\n"
        for i, (d, h, breaks) in enumerate(rating[:10], 1):
            msg += f"{i}. {d}д {h}ч | Срывов: {breaks}\n"
        await message.answer(msg)

    elif text == "мотивация":
        await message.answer(random.choice(praise_messages))

    elif text == "нофап сила":
        await message.answer(
            "Нофап — это контроль над собой. Когда ты держишься:\n\n"
            "💪 В качалке: больше энергии, больше силы и мотивации. "
            "Тело лучше откликается, мышцы растут быстрее.\n"
            "🎮 В Лиге Легенд: меньше тильтуешь, больше концентрации, быстрее принимаешь решения, апается рейтинг.\n"
            "🧠 В жизни: ясная голова, дисциплина, контроль эмоций, стабильность.\n\n"
            "Это путь к силе, фокусу и внутреннему спокойствию."
        )

    elif text == "нофап помощь":
        await message.answer(
            "📜 Команды NoFapWarden:\n"
            "нофап старт — начать путь / срыв\n"
            "мой нофап — твоя статистика\n"
            "ответом «нофап» — статистика человека\n"
            "топ нофаперов — рейтинг в чате\n"
            "мотивация — поддержка\n"
            "нофап сила — зачем это всё"
        )

    elif text == "нофап" and message.reply_to_message:
        target = message.reply_to_message.from_user
        user = get_user(target.id, message.chat.id)
        if user:
            days, hours = time_stats(user[2])
            await message.answer(f"{target.first_name} держится {days}д {hours}ч\n" + random.choice(praise_messages))

# -------------------- ALIVE LOOP --------------------
async def alive_loop():
    while True:
        await asyncio.sleep(1800)
        with db_lock:
            cursor.execute("SELECT DISTINCT chat_id FROM users")
            chats = cursor.fetchall()
        for (chat_id,) in chats:
            try:
                await bot.send_message(chat_id, random.choice(alive_messages))
            except:
                pass

# -------------------- ЗАПУСК --------------------
async def main():
    asyncio.create_task(alive_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
