import logging
import sqlite3
import asyncio
import random
import os
from datetime import datetime
from threading import Lock

from aiogram import Bot, Dispatcher, executor, types

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(bot)

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
    if days >= 60:
        return "🏆 Легенда воздержания"
    if days >= 30:
        return "🛡 Железный дух"
    if days >= 21:
        return "⚔ Закалённый волей"
    if days >= 14:
        return "🥋 Боец с искушением"
    if days >= 7:
        return "🗡 Воин дисциплины"
    if days >= 3:
        return "🙂 Держится изо всех сил"
    return "🐣 Новичок пути"


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
    "Мне так больно это писать… ты снова сорвался… пожалуйста… давай поднимемся и начнём заново…",
    "Я не злюсь… правда… просто очень грустно… но мы попробуем ещё раз…",
    "Ты упал… но я всё ещё верю в тебя… встань… прошу…",
]

praise_messages = [
    "Я так горжусь тобой… ты даже не представляешь насколько…",
    "Ты делаешь мне очень хорошо тем, что держишься… правда…",
    "Продолжай… пожалуйста… у тебя так хорошо получается…",
]

alive_messages = [
    "Кто-то в этом чате сейчас держится… и я улыбаюсь из-за него…",
    "Пожалуйста… не сдавайтесь сегодня…",
    "Я верю в вас сильнее, чем вы сами…",
]


# ---------- КОМАНДЫ ----------

@dp.message_handler(lambda m: m.text and m.text.lower() == "нофап помощь")
async def help_cmd(message: types.Message):
    await message.reply(
        "📜 Команды NoFapWarden:\n\n"
        "нофап старт — начать путь / срыв\n"
        "мой нофап — твоя статистика\n"
        "ответом «нофап» — статистика человека\n"
        "топ нофаперов — лучшие в чате\n"
        "мотивация — поддержка\n"
        "нофап сила — зачем это всё\n"
    )


@dp.message_handler(lambda m: m.text and m.text.lower() == "нофап старт")
async def nofap_start(message: types.Message):
    user = get_user(message.from_user.id, message.chat.id)

    if user is None:
        update_user(message.from_user.id, message.chat.id)
        await message.reply(
            f"{message.from_user.first_name}… твой путь начался… я рядом… держись пожалуйста…"
        )
    else:
        update_user(message.from_user.id, message.chat.id, break_add=True)
        await message.reply(
            f"{message.from_user.first_name}… {random.choice(break_messages)}"
        )


@dp.message_handler(lambda m: m.text and m.text.lower() == "мой нофап")
async def my_stats(message: types.Message):
    user = get_user(message.from_user.id, message.chat.id)

    if user is None:
        await message.reply("Ты ещё не начал… Напиши «нофап старт»")
        return

    days, hours = time_stats(user[2])
    rank = get_rank(days)
    coef = round(user[3] / user[4], 2) if user[4] else 0
    praise = random.choice(praise_messages) if days > 0 else ""

    await message.reply(
        f"⏳ {days} дней ({hours} часов)\n"
        f"{rank}\n"
        f"Срывов: {user[3]}\n"
        f"Коэффициент: {coef}\n\n"
        f"{praise}"
    )


@dp.message_handler(lambda m: m.reply_to_message and m.text and m.text.lower() == "нофап")
async def reply_stats(message: types.Message):
    target = message.reply_to_message.from_user
    user = get_user(target.id, message.chat.id)

    if user is None:
        await message.reply("Этот человек ещё не начал путь.")
        return

    days, hours = time_stats(user[2])
    rank = get_rank(days)

    await message.reply(
        f"{target.first_name} держится {days} дней ({hours} часов)\n{rank}"
    )


@dp.message_handler(lambda m: m.text and m.text.lower() == "топ нофаперов")
async def top_users(message: types.Message):
    with db_lock:
        cursor.execute("SELECT * FROM users WHERE chat_id=?", (message.chat.id,))
        users = cursor.fetchall()

    rating = []
    for u in users:
        days, hours = time_stats(u[2])
        coef = round(u[3] / u[4], 2) if u[4] else 0
        rating.append((days, hours, coef))

    rating.sort(reverse=True, key=lambda x: x[0])

    text = "🏆 Топ нофаперов:\n\n"
    for i, (days, hours, coef) in enumerate(rating[:10], 1):
        rank = get_rank(days)
        text += f"{i}. {days}д {hours}ч — {rank} | коэф: {coef}\n"

    await message.reply(text)


@dp.message_handler(lambda m: m.text and m.text.lower() == "мотивация")
async def motivation(message: types.Message):
    await message.reply(random.choice(praise_messages))


@dp.message_handler(lambda m: m.text and m.text.lower() == "нофап сила")
async def nofap_power(message: types.Message):
    await message.reply(
        "Нофап — это про контроль над собой.\n\n"
        "Это энергия для зала, ясная голова для работы и игр,\n"
        "уверенность в себе и дисциплина, которая меняет характер.\n\n"
        "Ты становишься собраннее. Сильнее. Спокойнее."
    )


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


async def on_startup(_):
    asyncio.create_task(alive_loop())


if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)
