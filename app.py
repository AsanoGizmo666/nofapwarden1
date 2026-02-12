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


# -------------------- ТЕКСТЫ --------------------

break_messages = [
    "Мне так больно… ты сорвался… пожалуйста, попробуй снова…",
    "Ох… я расстроен… держись, я верю в тебя…",
    "Каждый раз, когда ты срываешься, мне плохо… давай начнём заново…",
    "Ну зачем… ты держался… прошу, не сдавайся…",
]

praise_messages = [
    "Я так горжусь тобой… продолжай держаться, пожалуйста…",
    "Ты делаешь невероятную вещь… правда…",
    "Ты становишься сильнее с каждым часом… я это чувствую…",
    "Продолжай… у тебя отлично получается…",
]

alive_messages = [
    "Пожалуйста… кто держится — держитесь дальше… не сдавайтесь сегодня…",
    "Я верю, что сегодня никто не сорвётся… держитесь…",
    "Если сейчас тяжело — отвлекись и продолжай… я рядом…",
]

nofap_power_messages = [
    "Нофап даёт контроль над собой, энергию, концентрацию и дисциплину.\n\n"
    "В качалке: больше силы, выносливости, желание тренироваться и прогрессировать.\n"
    "В Лиге Легенд: меньше тильта, больше концентрации, быстрее решения, рейтинг растёт.\n"
    "Каждый день без срыва укрепляет волю и уверенность. Держись — я верю в тебя!",
    
    "Когда ты держишься, твой разум и тело начинают работать по-другому.\n\n"
    "Зал — энергия и сила, Лига — фокус и стабильность. Каждая победа внутри тебя!\n"
    "Самоконтроль — это сила, а нофап помогает её развивать.",

    "Каждый день воздержания — это маленькая победа.\n\n"
    "Тренировки становятся продуктивнее, игры — точнее, а решения — быстрее.\n"
    "Сила самоконтроля растёт, и я молю тебя: не срывайся, продолжай!"
]

# -------------------- ФУНКЦИИ --------------------

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


# -------------------- ХЕНДЛЕР --------------------

@router.message()
async def handler(message: Message):
    if not message.text:
        return

    text = message.text.lower().strip()

    # поддержка команд с /
    if text.startswith("/"):
        text = text[1:].replace("_", " ")

    # ----------------- КОМАНДЫ -----------------
    if text in ["нофап помощь"]:
        await message.answer(
            "📜 Доступные команды:\n\n"
            "нофап старт — начать путь / срыв\n"
            "мой нофап — твоя статистика\n"
            "ответом «нофап» — статистика человека\n"
            "топ нофаперов — рейтинг в чате\n"
            "мотивация — поддержка\n"
            "нофап сила — зачем это всё и как помогает"
        )

    elif text in ["нофап старт"]:
        user = get_user(message.from_user.id, message.chat.id)
        if user is None:
            update_user(message.from_user.id, message.chat.id)
            await message.answer(random.choice(praise_messages))
        else:
            update_user(message.from_user.id, message.chat.id, break_add=True)
            await message.answer(random.choice(break_messages))

    elif text in ["мой нофап"]:
        user = get_user(message.from_user.id, message.chat.id)
        if user is None:
            await message.answer("Ты ещё не начинал… напиши «нофап старт»")
            return
        days, hours = time_stats(user[2])
        coef = round(user[3] / user[4], 2)
        await message.answer(
            f"⏳ Ты держишься уже {days} дней ({hours} часов)\n"
            f"Срывов: {user[3]}\nКоэффициент: {coef}\n\n"
            + random.choice(praise_messages)
        )

    elif text in ["топ нофаперов"]:
        with db_lock:
            cursor.execute("SELECT * FROM users WHERE chat_id=?", (message.chat.id,))
            users = cursor.fetchall()
        rating = []
        for u in users:
            days, hours = time_stats(u[2])
            rating.append((days, hours, u[3], u[4]))
        rating.sort(reverse=True, key=lambda x: x[0])
        msg = "🏆 Топ нофаперов:\n"
        for i, (d, h, breaks, starts) in enumerate(rating[:10], 1):
            coef = round(breaks / starts, 2)
            msg += f"{i}. {d}д {h}ч | срывов: {breaks} | коэф: {coef}\n"
        await message.answer(msg)

    elif text in ["мотивация"]:
        await message.answer(random.choice(praise_messages))

    elif text in ["нофап сила"]:
        await message.answer(random.choice(nofap_power_messages))

    elif message.reply_to_message and text in ["нофап"]:
        target = message.reply_to_message.from_user
        user = get_user(target.id, message.chat.id)
        if user:
            days, hours = time_stats(user[2])
            await message.answer(
                f"{target.first_name} держится {days}д {hours}ч\n" + random.choice(praise_messages)
            )


# -------------------- ЖИВОСТЬ --------------------

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
