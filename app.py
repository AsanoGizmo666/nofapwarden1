import os
from flask import Flask, request
import telebot
from db import init_db, start_or_relapse, get_stats, top_users
from texts import relapse_text, start_text
from datetime import datetime

# Получаем токен из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не найден токен бота. Установите TELEGRAM_BOT_TOKEN в переменных окружения.")

# Создаём объект бота
bot = telebot.TeleBot(TOKEN)

# Создаём Flask приложение
app = Flask(__name__)

# Инициализируем базу
init_db()


def rank(days):
    if days < 3:
        return "Новобранец"
    if days < 7:
        return "Боец"
    if days < 14:
        return "Воин"
    if days < 30:
        return "Закалённый"
    return "Зверь"


@bot.message_handler(func=lambda m: m.text and m.text.lower() == "нофап старт")
def start(m):
    uid, cid = m.from_user.id, m.chat.id
    name = m.from_user.first_name

    status, days = start_or_relapse(uid, cid, name)

    if status == "start":
        bot.send_message(cid, start_text(1))
    else:
        bot.send_message(cid, relapse_text(days))


@bot.message_handler(commands=["стата"])
def stats(m):
    uid, cid = m.from_user.id, m.chat.id
    data = get_stats(uid, cid)

    if not data:
        bot.send_message(cid, "Ты даже не начинал. Напиши: нофап старт")
        return

    r = rank(data["days"])

    msg = f"""
📊 Твоя стата:

Дней: {data['days']}
Срывов: {data['relapses']}
Лучший стрик: {data['best']}
Звание: {r}
"""
    bot.send_message(cid, msg)


@bot.message_handler(commands=["топ"])
def top(m):
    cid = m.chat.id
    users = top_users(cid)

    table = []

    for u in users:
        name, start_date, relapses = u
        days = (datetime.now() -
                datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")).days
        score = days * 2 - relapses * 3
        table.append((name, days, relapses, score))

    table.sort(key=lambda x: x[3], reverse=True)

    text = "🏆 Топ нофаперов:\n\n"
    for i, u in enumerate(table[:5], 1):
        text += f"{i}. {u[0]} — {u[1]} дней | срывов {u[2]}\n"

    bot.send_message(cid, text)


# --- WEBHOOK ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@app.route("/")
def index():
    return "Bot is running", 200


if __name__ == "__main__":
    # Удаляем старый вебхук (если есть)
    bot.remove_webhook()
    # Устанавливаем новый вебхук на Bothost
    DOMAIN = os.getenv("DOMAIN")  # Например: bot_1770118607_9439_hanskapon.bothost.ru
    if not DOMAIN:
        raise ValueError("Не найден домен. Установите DOMAIN в переменных окружения Bothost.")
    bot.set_webhook(url=f"https://{DOMAIN}/{TOKEN}")
    
    # Запуск Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
