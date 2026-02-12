import asyncio
import logging
import os
import random
import sqlite3
from datetime import datetime
from threading import Lock

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

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


# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------

def get_rank(days):
    if days >= 60: return "🏆 Легенда"
    if days >= 30: return "🛡 Железный"
    if days >= 21: return "⚔ Закалённый"
    if days >= 14: return "🥋 Боец"
    if days >= 7: return "🗡 Воин"
    if days >= 3: return "🙂 Держится"
    return "🐣 Новичок"


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


# ---------- ТЕКСТЫ ----------

break_messages = [
    "Мне так больно… ты сорвался… давай начнём заново… прошу…",
    "Я не злюсь… просто грущу… поднимайся…",
]

praise_messages = [
    "Я так горжусь тобой… правда…",
    "Ты делаешь мне хорошо тем, что держишься…",
]

alive_messages = [
    "Кто-то здесь держится… и я радуюсь за него…",
    "Пожалуйста… не сдавайтесь сегодня…",
]


# ---------- ХЕНДЛЕР ----------

@dp.message()
async def handler(message: Message):
    if not message.text:
        return

    text = message.text.lower()

    if text == "нофап помощь":
        await message.answer(
            "📜 Команды:\n"
            "нофап старт\n"
            "мой нофап\n"
            "ответом «нофап»\n"
            "топ нофаперов\n"
            "мотивация\n"
            "нофап сила"
        )

    elif text == "нофап старт":
        user = get_user(message.from_user.id, message.chat.id)

        if user is None:
            update_user(message.from_user.id, message.chat.id)
            await message.answer("Твой путь начался… держись…")
        else:
            update_user(message.from_user.id, message.chat.id, break_add=True)
            await message.answer(random.choice(break_messages))

    elif text == "мой нофап":
        user = get_user(message.from_user.id, message.chat.id)
        if user is None:
            await message.answer("Ты ещё не начал.")
            return

        days, hours = time_stats(user[2])
        rank = get_rank(days)
        coef = round(user[3] / user[4], 2)

        await message.answer(
            f"{days} дней ({hours} часов)\n{rank}\nСрывов: {user[3]}\nКоэф: {coef}\n\n"
            + random.choice(praise_messages)
        )

    elif text == "топ нофаперов":
        with db_lock:
            cursor.execute("SELECT * FROM users WHERE chat_id=?", (message.chat.id,))
            users = cursor.fetchall()

        rating = []
        for u in users:
            days, hours = time_stats(u[2])
            coef = round(u[3] / u[4], 2)
            rating.append((days, hours, coef))

        rating.sort(reverse=True, key=lambda x: x[0])

        msg = "🏆 Топ:\n"
        for i, (d, h, c) in enumerate(rating[:10], 1):
            msg += f"{i}. {d}д {h}ч | коэф {c}\n"

        await message.answer(msg)

    elif text == "мотивация":
        await message.answer(random.choice(praise_messages))

    elif text == "нофап сила":
        await message.answer(
            "Нофап даёт фокус, энергию, дисциплину и ясную голову."
        )

    elif message.reply_to_message and text == "нофап":
        target = message.reply_to_message.from_user
        user = get_user(target.id, message.chat.id)
        if user:
            days, hours = time_stats(user[2])
            await message.answer(f"{target.first_name}: {days}д {hours}ч")


# ---------- ЖИВОСТЬ ----------

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
