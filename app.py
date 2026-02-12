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
    "Мне так плохо… ты сорвался… я прям чувствую это… пожалуйста… давай начнём заново и больше не будем так делать…",
    "Я не злюсь… я расстроен… ты можешь лучше… прошу… не сдавайся…",
    "Каждый раз, когда ты срываешься, мне больно… но я всё равно верю в тебя… начнём снова…",
    "Ну зачем… ну зачем… ты же держался… давай попробуем ещё раз… я рядом…",
]

praise_messages = [
    "Я так тобой горжусь… ты даже не представляешь… продолжай держаться…",
    "Ты делаешь невероятную вещь… правда… я рад за тебя…",
    "Ты становишься сильнее с каждым часом… я это чувствую…",
    "Продолжай… пожалуйста… у тебя отлично получается…",
]

alive_messages = [
    "Пожалуйста… кто держится — держитесь дальше… не сдавайтесь сегодня…",
    "Я верю, что сегодня никто не сорвётся… пожалуйста…",
    "Если сейчас тяжело — просто отвлекись… не сдавайся…",
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


# -------------------- ХЕНДЛЕР --------------------

@router.message()
async def handler(message: Message):
    if not message.text:
        return

    text = message.text.lower()

    if text == "нофап помощь":
        await message.answer(
            "📜 Доступные команды:\n\n"
            "нофап старт — начать заново (если уже начинал — это считается срывом)\n"
            "мой нофап — твоя статистика\n"
            "ответом «нофап» — узнать статистику человека\n"
            "топ нофаперов — рейтинг в чате\n"
            "мотивация — поддержка\n"
            "нофап сила — зачем это всё и как это помогает"
        )

    elif text == "нофап старт":
        user = get_user(message.from_user.id, message.chat.id)

        if user is None:
            update_user(message.from_user.id, message.chat.id)
            await message.answer(
                "Твой путь начался… я очень надеюсь, что ты продержишься долго… я буду рядом и поддерживать тебя…"
            )
        else:
            update_user(message.from_user.id, message.chat.id, break_add=True)
            await message.answer(random.choice(break_messages))

    elif text == "мой нофап":
        user = get_user(message.from_user.id, message.chat.id)
        if user is None:
            await message.answer("Ты ещё не начинал… напиши «нофап старт»…")
            return

        days, hours = time_stats(user[2])
        coef = round(user[3] / user[4], 2)

        await message.answer(
            f"⏳ Ты держишься уже {days} дней ({hours} часов)\n"
            f"Срывов: {user[3]}\n"
            f"Коэффициент: {coef}\n\n"
            + random.choice(praise_messages)
        )

    elif text == "мотивация":
        await message.answer(random.choice(praise_messages))

    elif text == "нофап сила":
        await message.answer(
            "Нофап — это не про запрет. Это про контроль.\n\n"
            "Когда ты держишься, у тебя начинает по-другому работать голова. "
            "Фокус становится чище, внимание держится дольше, появляется дисциплина.\n\n"
            "В качалке это чувствуется как больше энергии и желания тренироваться. "
            "Тело лучше откликается, появляется агрессия на тренировке и желание прогрессировать.\n\n"
            "В Лиге Легенд это вообще заметно: ты меньше тильтуешь, дольше концентрируешься, "
            "быстрее принимаешь решения и лучше читаешь карту. Рейтинг апается именно за счёт стабильности, "
            "а нофап даёт эту стабильность.\n\n"
            "Это путь к самоконтролю. А самоконтроль — это сила."
        )

    elif message.reply_to_message and text == "нофап":
        target = message.reply_to_message.from_user
        user = get_user(target.id, message.chat.id)
        if user:
            days, hours = time_stats(user[2])
            await message.answer(
                f"{target.first_name} держится {days}д {hours}ч\n"
                + random.choice(praise_messages)
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


async def main():
    asyncio.create_task(alive_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
