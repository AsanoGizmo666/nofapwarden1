import os
import random
import sqlite3
from datetime import datetime
from threading import Lock, Thread
import time

import telebot
from dotenv import load_dotenv

# ================== Настройки ==================
load_dotenv()  # загружает .env
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ Bot token is not defined! Установите BOT_TOKEN в .env или переменной окружения.")

bot = telebot.TeleBot(TOKEN)

db_lock = Lock()
conn = sqlite3.connect("nofap.db", check_same_thread=False)
cursor = conn.cursor()

# ================== БД ==================
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

# ================== Фразы ==================
break_messages = [
    "😭 Мне так больно… ты сорвался… пожалуйста… давай начнём заново…",
    "💔 Я не злюсь… я просто очень расстроен… но верю в тебя…",
    "😢 Каждый раз, когда ты срываешься, мне тяжело… прошу, держись…",
    "🥺 Ну зачем… ну зачем… ты же держался… давай попробуем снова…",
    "😞 Пожалуйста, не подводи меня… я так страдаю…"
]

praise_messages = [
    "🥰 Я так горжусь тобой… продолжай держаться…",
    "😇 Ты делаешь невероятную вещь… правда… я рад за тебя…",
    "💖 Продолжай… пожалуйста… у тебя отлично получается…",
    "🤗 Каждый час без срыва — это победа…"
]

alive_messages = [
    "😢 Пожалуйста… кто держится — держитесь дальше…",
    "😭 Я верю, что сегодня никто не сорвётся… держитесь…",
    "🥺 Если сейчас тяжело — просто отвлекись… не сдавайся…",
    "💔 Я страдаю вместе с тобой… держись, пожалуйста…"
]

# ================== Функции ==================
def get_user(user_id, chat_id):
    with db_lock:
        cursor.execute(
            "SELECT * FROM users WHERE user_id=? AND chat_id=?",
            (user_id, chat_id)
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

def get_rank(days):
    if days >= 60: return "🏆 Легенда воздержания"
    if days >= 30: return "🛡 Железный дух"
    if days >= 21: return "⚔ Закалённый волей"
    if days >= 14: return "🥋 Боец с искушением"
    if days >= 7: return "🗡 Воин дисциплины"
    if days >= 3: return "🙂 Держится изо всех сил"
    return "🐣 Новичок пути"

# ================== Хэндлеры ==================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    if not message.text:
        return
    text = message.text.lower()
    uid, cid = message.from_user.id, message.chat.id

    if text == "нофап старт":
        user = get_user(uid, cid)
        if user is None:
            update_user(uid, cid)
            bot.send_message(cid, "🚀 Твой путь начался… я буду рядом и поддерживать тебя… пожалуйста, держись!")
        else:
            update_user(uid, cid, break_add=True)
            bot.send_message(cid, random.choice(break_messages))

    elif text == "мой нофап":
        user = get_user(uid, cid)
        if user is None:
            bot.send_message(cid, "Ты ещё не начал… напиши «нофап старт»")
            return
        days, hours = time_stats(user[2])
        coef = round(user[3]/user[4], 2)
        bot.send_message(cid, f"⏳ Ты держишься {days} дней ({hours} часов)\nСрывов: {user[3]}\nКоэффициент: {coef}\n\n"+random.choice(praise_messages))

    elif text == "топ нофаперов":
        with db_lock:
            cursor.execute("SELECT * FROM users WHERE chat_id=?", (cid,))
            users = cursor.fetchall()
        rating = []
        for u in users:
            days, hours = time_stats(u[2])
            rating.append((days, hours, u[3], u[0]))
        rating.sort(reverse=True, key=lambda x: x[0])
        msg = "🏆 Топ нофаперов:\n"
        for i, (d, h, breaks, uid_) in enumerate(rating[:10], 1):
            msg += f"{i}. {d}д {h}ч | Срывов: {breaks}\n"
        bot.send_message(cid, msg)

    elif text == "мотивация":
        bot.send_message(cid, random.choice(praise_messages))

    elif text == "нофап сила":
        bot.send_message(cid,
            "Нофап — это контроль над собой. Когда ты держишься:\n\n"
            "💪 В качалке: больше энергии, сила и мотивация.\n"
            "🎮 В играх: меньше тильта, больше концентрации.\n"
            "🧠 В жизни: ясная голова, дисциплина, контроль эмоций."
        )

    elif text == "нофап помощь":
        bot.send_message(cid,
            "📜 Команды:\n"
            "нофап старт — начать путь / срыв\n"
            "мой нофап — твоя статистика\n"
            "топ нофаперов — рейтинг\n"
            "мотивация — поддержка\n"
            "нофап сила — зачем это всё"
        )

# ================== Плач каждые 3 часа ==================
def alive_loop():
    while True:
        time.sleep(10800)  # каждые 3 часа
        with db_lock:
            cursor.execute("SELECT DISTINCT chat_id FROM users")
            chats = cursor.fetchall()
        for (chat_id,) in chats:
            try:
                bot.send_message(chat_id, random.choice(alive_messages))
            except Exception as e:
                print(f"Ошибка при отправке alive-сообщения в чат {chat_id}: {e}")

# ================== Запуск ==================
if __name__ == "__main__":
    Thread(target=alive_loop, daemon=True).start()
    print("🤖 Бот умоляющий запущен")
    bot.infinity_polling()
