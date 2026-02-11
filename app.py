import os
import telebot
from datetime import datetime, timedelta
from random import choice
from db import init_db, start_or_relapse, get_stats, top_users, add_goal, check_goal, add_relapse, get_last_relapses, get_user_last_activity, add_achievement

# --- Настройки ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Установите TELEGRAM_BOT_TOKEN в переменных окружения!")

bot = telebot.TeleBot(TOKEN)
init_db()

# --- Звания ---
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

# --- Помощь ---
HELP_TEXT = """
📝 Команды:
- нофап старт — начать путь / зафиксировать прогресс
- стата — показать RPG-профиль
- топ — топ участников
- позор — последние срывы
- на грани — мотивация
- мягкая мотивация — лёгкая поддержка
- жёсткая мотивация — жёсткий мотиватор
- выдержу N — заявить цель на N дней
- нофап помощь — показать команды
"""

# --- Команды ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "нофап старт")
def cmd_start(m):
    uid, cid, name = m.from_user.id, m.chat.id, m.from_user.first_name
    status, days = start_or_relapse(uid, cid, name)
    if status == "start":
        bot.send_message(cid, f"{name}, первый день зафиксирован! 💪")
    else:
        bot.send_message(cid, f"{name}, срыв зафиксирован, текущий прогресс: {days} дней.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "стата")
def cmd_stats(m):
    uid, cid = m.from_user.id, m.chat.id
    data = get_stats(uid, cid)
    if not data:
        bot.send_message(cid, "Ты ещё не начинал. Напиши: нофап старт")
        return
    days = data["days"]
    relapses = data["relapses"]
    ach = data.get("achievements", [])
    hidden = data.get("hidden_achievements", [])
    msg = f"""
🧠 Сила воли: {days}
💀 Срывов: {relapses}
🏅 Звание: {rank_name(days)}
📉 Индекс слабости: {round(relapses/max(1,days)*100)}%
🟢 Индекс честности: высокий
🏆 Ачивки: {', '.join(ach) if ach else 'нет'}
🤫 Тайные ачивки: {', '.join(hidden) if hidden else 'нет'}
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
    text = "🏆 Топ участников:\n\n"
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

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "на грани")
def cmd_edge(m):
    phrases = [
        "Не сегодня! Ты сильнее этого.",
        "Срывы — для слабых. Ты не слабый.",
        "Встань и покажи, кто тут Воин!",
        "Каждый день без срыва делает тебя Зверем."
    ]
    bot.send_message(m.chat.id, choice(phrases))

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "мягкая мотивация")
def cmd_soft_motivation(m):
    phrases = [
        "Держись, сегодня всё под контролем.",
        "Маленький шаг сегодня — большой результат завтра.",
        "Ты можешь это! Продолжай."
    ]
    bot.send_message(m.chat.id, choice(phrases))

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "жёсткая мотивация")
def cmd_hard_motivation(m):
    phrases = [
        "Срывы — для слабых. Держись или капитулируй!",
        "Каждый день без контроля — шаг назад!",
        "Хватит жалеть себя, вставай и действуй!"
    ]
    bot.send_message(m.chat.id, choice(phrases))

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("выдержу"))
def cmd_goal(m):
    uid, cid, name = m.from_user.id, m.chat.id, m.from_user.first_name
    try:
        days_goal = int(m.text.split()[1])
        add_goal(uid, cid, name, days_goal)
        bot.send_message(cid, f"{name}, цель на {days_goal} дней зафиксирована! 💪")
    except:
        bot.send_message(cid, "Напиши: выдержу N — где N это количество дней.")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "нофап помощь")
def cmd_help(m):
    bot.send_message(m.chat.id, HELP_TEXT)

# --- Опасные дни ---
def check_danger_days():
    from db import get_all_users
    for uid, name, cid, start_date, relapses in get_all_users():
        days = (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")).days
        if days in [2,3,7,14,30,60,90]:
            bot.send_message(cid, f"⚠️ {rank_phrase(name, days)} Сегодня опасный день!")

# --- Long Polling ---
if __name__ == "__main__":
    import threading, time
    def danger_loop():
        while True:
            check_danger_days()
            time.sleep(60*60*6)
    threading.Thread(target=danger_loop, daemon=True).start()

    print("🔥 Прокачанный Нофап Бот запущен через long polling...")
    bot.infinity_polling()

