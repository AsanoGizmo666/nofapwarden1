import os
import telebot
from telebot import types
from datetime import datetime, timedelta
from random import choice
import threading, time
from db import (
    init_db, start_or_relapse, get_stats, top_users,
    add_relapse, get_last_relapses, get_user_last_activity,
    get_all_users, add_achievement, get_achievements
)

# ------------------ НАСТРОЙКИ ------------------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Установите TELEGRAM_BOT_TOKEN в переменных окружения!")

bot = telebot.TeleBot(TOKEN)
init_db()

# ------------------ ЗВАНИЯ ------------------
def rank_name(days):
    if days < 3: return "Новобранец"
    if days < 7: return "Боец"
    if days < 14: return "Воин"
    if days < 30: return "Закалённый"
    if days < 60: return "Зверь"
    if days < 90: return "Терминатор"
    return "Легенда"

def rank_phrase(name, days):
    r = rank_name(days)
    phrases = {
        "Новобранец": "Впервые на пути, ещё тряпка!",
        "Боец": "Ты уже держишься, но не расслабляйся!",
        "Воин": "Сила воли крепкая, но испытания ждут!",
        "Закалённый": "Закалённый духом, почти сталь!",
        "Зверь": "Невероятно, твоя сила воли впечатляет!",
        "Терминатор": "Терминатор! Почти легенда!",
        "Легенда": "Ты легенда, перед тобой все капитулируют!"
    }
    return f"{r} {name}, {days} дней. {phrases[r]}"

# ------------------ АЧИВКИ ------------------
ACHIEVEMENTS = [
    ("Пережил ад", 3),
    ("Перелом", 7),
    ("Перезагрузка", 30),
    ("Нечеловеческий", 90)
]

def check_achievements(uid, cid, days):
    for title, threshold in ACHIEVEMENTS:
        if days >= threshold and title not in get_achievements(uid, cid):
            add_achievement(uid, cid, title)
            bot.send_message(cid, f"🏆 {title}! Поздравляем!")

# ------------------ ПОМОЩЬ ------------------
HELP_TEXT = """
📝 Команды бота:
- нофап старт — начать путь / зафиксировать прогресс
- стата — показать свой RPG-профиль
- топ — топ участников
- позор — последние срывы в группе
- я на грани — моментальная мотивация с голосованием
- нофап помощь — показать список команд
"""

# ------------------ КОМАНДЫ ------------------
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "нофап старт")
def cmd_start(m):
    uid, cid, name = m.from_user.id, m.chat.id, m.from_user.first_name
    status, days = start_or_relapse(uid, cid, name)
    if status == "start":
        bot.send_message(cid, f"{name} начал путь! Первый день пройден ✅")
    else:
        bot.send_message(cid, f"{name} сорвался! Текущий прогресс: {days} дней")
    check_achievements(uid, cid, days)

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "стата")
def cmd_stats(m):
    uid, cid = m.from_user.id, m.chat.id
    data = get_stats(uid, cid)
    if not data:
        bot.send_message(cid, "Ты даже не начинал. Напиши: нофап старт")
        return
    r = rank_name(data["days"])
    weakness = round(data["relapses"]/max(1,data["days"])*100)
    msg = f"""
🧠 Сила воли: {data['days']}
💀 Срывов: {data['relapses']}
🏅 Звание: {r}
📉 Индекс слабости: {weakness}%
🟢 Индекс честности: высокий
Ачивки: {', '.join(get_achievements(uid, cid)) or 'Нет'}
"""
    bot.send_message(cid, msg)

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "топ")
def cmd_top(m):
    cid = m.chat.id
    users = top_users(cid)
    table = []
    for u in users:
        name, start_date, relapses = u
        days = (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")).days
        score = days*2 - relapses*3
        table.append((name, days, relapses, score))
    table.sort(key=lambda x: x[3], reverse=True)
    text = "🏆 Топ нофаперов:\n\n"
    for i,u in enumerate(table[:5],1):
        text += f"{i}. {u[0]} — {u[1]} дней | срывов {u[2]}\n"
    bot.send_message(cid, text)

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "позор")
def cmd_pozor(m):
    cid = m.chat.id
    last = get_last_relapses(cid)
    if not last:
        bot.send_message(cid, "Пока никто не сорвался 😏")
        return
    text = "💀 Последние падшие:\n\n"
    for name, days in last:
        text += f"{name} — сорвался на {days} дне\n"
    bot.send_message(cid, text)

# ------------------ «На грани» с голосованием ------------------
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "я на грани")
def cmd_edge(m):
    cid = m.chat.id
    uid = m.from_user.id
    name = m.from_user.first_name

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👍 Держим", callback_data=f"edge_trust_{uid}"))
    markup.add(types.InlineKeyboardButton("👎 Пусть сорвется", callback_data=f"edge_doubt_{uid}"))

    bot.send_message(cid, f"⚡ {name} на грани! Поддержим его?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "нофап помощь")
def cmd_help(m):
    bot.send_message(m.chat.id, HELP_TEXT)

# ------------------ ФОН, ЕЖЕДНЕВНАЯ СВОДКА, СТРАВЛИВАНИЕ ------------------
def background_loop():
    while True:
        try:
            users = get_all_users()
            # --- опасные дни и подозрительные ---
            for uid, name, cid, start_date, relapses in users:
                days = (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")).days
                if days in [2,3,7,14,30,60,90]:
                    bot.send_message(cid, f"⚠️ {rank_phrase(name, days)} Сегодня опасный день!")
                # Подозрительные молчуны
                last_activity = get_user_last_activity(uid, cid)
                if last_activity and (datetime.now() - last_activity).days >= 5:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("👍 Верим", callback_data=f"trust_{uid}"))
                    markup.add(types.InlineKeyboardButton("👎 Сомневаемся", callback_data=f"doubt_{uid}"))
                    bot.send_message(cid, f"🤨 {name} слишком тихий для {days} дней. Проверяем?", reply_markup=markup)

            # --- стравливание топ-2 ---
            groups = {}
            for uid, name, cid, start_date, relapses in users:
                days = (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")).days
                groups.setdefault(cid, []).append((name, days))
            for cid, lst in groups.items():
                if len(lst) >= 2:
                    lst.sort(key=lambda x: x[1], reverse=True)
                    diff = lst[0][1] - lst[1][1]
                    if diff > 0:
                        bot.send_message(cid, f"🔥 {lst[1][0]} отстаёт от {lst[0][0]} на {diff} дней! Не расслабляйся!")

            # --- ежедневная сводка группы ---
            for cid, lst in groups.items():
                summary = {}
                for name, days in lst:
                    r = rank_name(days)
                    summary[r] = summary.get(r, 0) + 1
                text = "📣 Сегодня в группе:\n"
                for r, count in summary.items():
                    text += f"{count} {r}\n"
                bot.send_message(cid, text)

        except Exception as e:
            print("Ошибка фонового потока:", e)
        time.sleep(60*60*6)  # каждые 6 часов

# ------------------ ОБРАБОТКА ГОЛОСОВАНИЙ ------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_vote(call):
    data = call.data
    cid = call.message.chat.id
    if data.startswith("trust_"):
        bot.send_message(cid, f"👍 Сообщество верит в честность!")
    elif data.startswith("doubt_"):
        bot.send_message(cid, f"👎 Сообщество сомневается в честности. {call.message.text.splitlines()[0]}")
    elif data.startswith("edge_trust_"):
        bot.send_message(cid, f"💪 Сообщество поддерживает {call.message.text.splitlines()[0].split()[0]}! Держимся вместе!")
    elif data.startswith("edge_doubt_"):
        bot.send_message(cid, f"😅 Сообщество сомневается в {call.message.text.splitlines()[0].split()[0]}… Но мы верим, что справится!")
    try:
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
    except:
        pass

# ------------------ LONG POLLING ------------------
if __name__ == "__main__":
    threading.Thread(target=background_loop, daemon=True).start()
    print("🔥 Суперпрокачанный нофап бот запущен!")
    bot.infinity_polling()
