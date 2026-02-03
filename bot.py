import telebot
import sqlite3
import schedule
import time
import threading
import random
import os
from datetime import datetime, timedelta

# ==================== БЕЗОПАСНОЕ ПОЛУЧЕНИЕ ТОКЕНА ====================
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    try:
        with open('token.txt', 'r') as f:
            TOKEN = f.read().strip()
    except FileNotFoundError:
        pass

if not TOKEN:
    error_msg = """
    ОШИБКА: Токен бота не найден!
    
    СПОСОБЫ УСТАНОВКИ ТОКЕНА:
    1. ДЛЯ BOTHOST.RU (рекомендуется):
       - В панели управления создайте переменную окружения:
         Ключ: TELEGRAM_BOT_TOKEN
         Значение: ваш токен от @BotFather
    
    2. ДЛЯ ЛОКАЛЬНОГО ЗАПУСКА:
       - Создайте файл token.txt в одной папке с ботом
       - Вставьте в него токен (только токен, без кавычек)
    """
    print(error_msg)
    raise ValueError("Токен бота не найден. См. инструкцию выше.")

bot = telebot.TeleBot(TOKEN)
# =====================================================================

# --- БАЗА ДАННЫХ ---
def db_query(query, params=(), fetch=False):
    with sqlite3.connect('nofap_ultra.db') as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if fetch: 
            return cur.fetchall()
        conn.commit()

db_query('''CREATE TABLE IF NOT EXISTS users 
            (id INTEGER, chat_id INTEGER, username TEXT, start_time TEXT, 
             last_start_time TEXT, attempts INTEGER, total_days INTEGER,
             current_streak INTEGER, PRIMARY KEY(id, chat_id))''')

# --- ЖЁСТКАЯ МОТИВАЦИЯ И УНИЖЕНИЯ ---
HARD_MOTIVATION = [
    "💪 Ты думаешь, успех даётся слабакам? Каждый раз, когда ты срываешься, ты отдаляешь свою мечту.",
    "🧠 Мозг слабака ищет лёгкий дофамин. Мозг мужчины строит реальность. Кто ты?",
    "🦁 В стае львов нет места тем, кто не контролирует свои инстинкты. Будь львом, а не шакалом.",
    "⚡️ Сила воли — это не дар. Это выбор. Каждый день. Каждый час. Ты выбираешь быть сильным или снова провалиться?",
    "🔥 Пока ты тратишь энергию в пустоту, другие строят карьеру, тело, жизнь. Проснись.",
    "🎯 Цель настоящего мужчины — не получить мгновенное удовольствие, а построить что-то стоящее. Ты строишь или разрушаешь?",
    "🏔️ На вершину не пускают тех, кто не может пройти путь. Твой путь начинается с контроля над собой.",
    "🛡️ Самодисциплина — это доспехи мужчины в мире, полном соблазнов. Ты воин или мишень?",
    "💎 Ценность мужчины определяется тем, чем он жертвует ради цели. Ты жертвуешь сиюминутным ради великого?",
    "🚀 Будущий ты смотрит на тебя сейчас. Он гордится тобой или стыдится? Выбор за тобой."
]

HARD_INSULTS = [
    "🤡 Ещё один раз и ты официально клоун. Клоуны развлекают других, мужчины достигают целей.",
    "👋 Твоя рука уже устала от тебя. Может, хватит быть мальчиком и пора стать мужчиной?",
    "📉 Каждый срыв — это минус к твоей мужской состоятельности. Счёт уже отрицательный.",
    "🐌 Ты ползёшь по жизни, пока другие бегут. Разница в том, что они контролируют себя.",
    "🦾 'Профессиональный неудачник' — звучит гордо? Нет. Перестань быть профаном в своей же жизни.",
    "🧀 Твоя воля как сырок — тает при малейшем напряжении. Мужики не тают, они держат удар.",
    "🚽 Ты всерьёз думаешь, что твоё предназначение — сливать потенциал в канализацию? Очнись.",
    "🧦 Даже носки служат дольше, чем твоя решимость. Прими это и изменись.",
    "👹 Ты смотришь на мир через призму слабости. Настоящие мужчины смотрят на мир как на поле битвы, где они побеждают.",
    "🐒 Инстинкты правят тобой. Эволюция прошла мимо. Поднимись с колен, двуногий."
]

# Научные факты остаются серьёзными
SCIENTIFIC_FACTS = [
    {
        "title": "📊 НАУКА: Тестостерон +45.7% за 7 дней",
        "content": "Исследование Journal of Sexual Medicine: после 7 дней воздержания уровень тестостерона повышается на 45.7%. Это не мнение — это измерение в крови.",
        "source": "Journal of Sexual Medicine, 2021",
        "benefit": "Больше силы, уверенности, мужской энергии"
    },
    {
        "title": "🧠 ФАКТ: Мозг восстанавливается",
        "content": "fMRI-исследования показывают: префронтальная кора (отвечает за контроль) активируется при воздержании. Ты буквально качаешь мозг.",
        "source": "Frontiers in Psychiatry, 2020",
        "benefit": "Лучший контроль, ясность ума, решимость"
    },
    {
        "title": "💪 РЕАЛЬНОСТЬ: Энергия = результат",
        "content": "89% мужчин в исследовании отметили: через 2 недели чистоты появляется энергия, которой хватает на спорт, работу и цели.",
        "source": "International Journal of Impotence Research",
        "benefit": "Энергия для достижений, а не для прокрастинации"
    }
]

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_progress_bar(value, max_value=100, length=10):
    filled = int((value / max_value) * length)
    return '█' * filled + '░' * (length - filled)

def get_user_status_message(days, attempts, name):
    """Получить сообщение в зависимости от статистики"""
    if days == 0:
        return "Ты ещё даже не начал. Слабовато."
    
    if attempts == 0 and days < 3:
        return f"🔥 {name}, ты только начал. Не подведи себя."
    elif attempts == 0 and days >= 7:
        return f"💪 {name}, 7+ дней без срывов. Так держать, мужик!"
    elif attempts == 0 and days >= 30:
        return f"🏆 {name}, месяц чистоты. Ты на правильном пути, воин."
    
    if attempts > 0 and days < 3:
        insult = random.choice(HARD_INSULTS)
        return f"📉 {name}, {attempts} срывов. {insult}"
    elif attempts > 3 and days < 7:
        return f"⚠️ {name}, {attempts} срывов. Ты серьёзно? Соберись, блин."
    else:
        motivation = random.choice(HARD_MOTIVATION)
        return f"🎯 {name}, {days} дней. {motivation}"

# --- КОМАНДЫ ---
@bot.message_handler(commands=['помощь', 'help', 'start'])
def show_help(m):
    help_text = """
🔬 *НОФАП: ЖЕСТКИЙ РЕЖИМ* 🔬

*ОСНОВНЫЕ КОМАНДЫ:*
▶️ `/старт` или `нофап старт` - начать/перезапустить
📊 `/стат` - твоя статистика (без жалости)
🔬 `/факт` - научные данные (суровая правда)
💢 `/мотивация` - жёсткая правда для мужчин
👊 `/удар` - порция правды о твоих срывах
👥 `/топ` - кто здесь мужик, а кто нет

*ДОПОЛНИТЕЛЬНО:*
📊 `мой нофап` - базовая статистика
👤 Ответить на сообщение + `нофап` - статистика другого

*ПРАВИЛА:*
1. Никаких оправданий
2. Либо делаешь, либо нет
3. Наука на твоей стороне, если ты на своей
    """
    bot.reply_to(m, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['удар'])
def hard_feedback(m):
    """Жёсткая обратная связь"""
    user_id, chat_id = m.from_user.id, m.chat.id
    
    res = db_query("SELECT start_time, attempts, username FROM users WHERE id = ? AND chat_id = ?", 
                   (user_id, chat_id), fetch=True)
    
    if not res:
        response = "🤡 Ты даже не начал, а уже хочешь мотивации? Сначала `/старт`, потом поговорим."
        bot.reply_to(m, response, parse_mode="Markdown")
        return
    
    start_dt_str, attempts, username = res[0]
    start_dt = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_dt).days
    
    if attempts == 0:
        if days < 7:
            response = f"💪 {username}, ты держишься {days} дней без срывов. Не расслабляйся — самые тяжёлые дни впереди."
        elif days < 30:
            response = f"🔥 {username}, {days} дней — уже что-то. Но месяц — это минимум для перезагрузки. Не сбивайся."
        else:
            response = f"🏆 {username}, {days} дней. Ты доказал, что можешь. Теперь докажи, что сможешь всегда."
    else:
        if days < 3:
            insult = random.choice(HARD_INSULTS)
            response = f"📉 {username}, {attempts} срывов за {days} дней? {insuit}"
        else:
            response = f"⚠️ {username}, {days} дней, но {attempts} срывов. Соотношение говорит само за себя. Исправляй."
    
    bot.reply_to(m, response, parse_mode="Markdown")

@bot.message_handler(commands=['топ'])
def group_top(m):
    """Топ участников группы"""
    chat_id = m.chat.id
    
    res = db_query('''SELECT username, current_streak, attempts 
                      FROM users WHERE chat_id=? 
                      ORDER BY current_streak DESC, attempts ASC 
                      LIMIT 5''', (chat_id,), fetch=True)
    
    if not res:
        bot.reply_to(m, "📊 *Топ пока пустой*\nКто будет первым мужиком? `/старт`", parse_mode="Markdown")
        return
    
    top_text = "🏆 *ТОП МУЖИКОВ ГРУППЫ* 🏆\n\n"
    
    for i, (name, streak, attempts) in enumerate(res, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔸"
        status = "ЖЕЛЕЗНЫЙ" if streak > 30 else "СТАЛЬНОЙ" if streak > 14 else "НОВИЧОК"
        top_text += f"{medal} *{name or 'Аноним'}* — {streak} дней ({status})\n"
        top_text += f"   Срывов: {attempts} | Эффективность: {round(streak/(streak+attempts)*100 if streak+attempts>0 else 100)}%\n\n"
    
    if len(res) < 3:
        top_text += "\n⚠️ *Мест всего 5. Занять их может каждый.*\n"
        top_text += "🔥 *Будь в топе или будь как все.*\n"
    
    top_text += "\n📊 Твоя статистика: `/стат`"
    
    bot.reply_to(m, top_text, parse_mode="Markdown")

@bot.message_handler(commands=['стат'])
def show_stats_hard(m):
    """Жёсткая статистика"""
    user_id, chat_id = m.from_user.id, m.chat.id
    
    res = db_query("SELECT start_time, attempts, username, current_streak FROM users WHERE id = ? AND chat_id = ?", 
                   (user_id, chat_id), fetch=True)
    
    if not res:
        bot.reply_to(m, "❌ *Ты даже не начал.*\nСначала докажи, что ты способен на `/старт`", parse_mode="Markdown")
        return
    
    start_dt_str, attempts, username, current_streak = res[0]
    start_dt = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_dt).days
    
    # Обновляем стрик
    db_query("UPDATE users SET current_streak=? WHERE id=? AND chat_id=?", 
             (days, user_id, chat_id))
    
    # Оценка
    if attempts == 0:
        rating = "ЖЕЛЕЗНЫЙ" if days > 30 else "СТОЙКИЙ" if days > 14 else "НАЧАЛЬНЫЙ"
        rating_emoji = "🔴" if days < 7 else "🟡" if days < 21 else "🟢"
    else:
        efficiency = days/(days+attempts)*100 if days+attempts>0 else 0
        if efficiency > 80:
            rating = "ВОССТАНАВЛИВАЕТСЯ"
            rating_emoji = "🟢"
        elif efficiency > 50:
            rating = "НЕСТАБИЛЬНЫЙ"
            rating_emoji = "🟡"
        else:
            rating = "СЛАБАК"
            rating_emoji = "🔴"
    
    # Прогресс-бары
    progress_7 = min(100, (days / 7) * 100)
    progress_30 = min(100, (days / 30) * 100)
    
    stats_msg = f"""
📊 *СТАТИСТИКА: {username or 'АНОНИМ'}* {rating_emoji}
{'═' * 35}

📅 *Текущий стрик:* {days} дней
📉 *Всего срывов:* {attempts}
🏆 *Рейтинг:* {rating}
📈 *Эффективность:* {round(days/(days+attempts)*100 if days+attempts>0 else 0, 1)}%

🎯 *ПРОГРЕСС:*
7 дней (тестостерон +45%): {get_progress_bar(progress_7)} {round(progress_7)}%
30 дней (перезагрузка): {get_progress_bar(progress_30)} {round(progress_30)}%

{'⚠️ ТЕБЕ НУЖЕН УДАР' if attempts > days/2 else '💪 ТЫ НА ПРАВИЛЬНОМ ПУТИ' if days > 7 else '🔥 НАЧАЛО ПОЛОЖЕНО'}
"""
    
    if attempts > 0 and days < 7:
        stats_msg += f"\n📉 *ФАКТ:* {attempts} срывов за {days} дней = слабая воля. Исправляй."
    elif days >= 30:
        stats_msg += f"\n🏆 *ФАКТ:* {days} дней — ты доказал, что можешь. Теперь сделай это нормой."
    
    bot.reply_to(m, stats_msg, parse_mode="Markdown")

@bot.message_handler(commands=['факт'])
def send_scientific_fact(m):
    """Научный факт"""
    fact = random.choice(SCIENTIFIC_FACTS)
    
    fact_msg = f"""
🔬 *НАУКА, А НЕ БОЛТОВНЯ* 🔬

*{fact['title']}*

{fact['content']}

📚 *Источник:* {fact['source']}
✅ *Что это тебе даёт:* {fact['benefit']}

💪 *Вывод:* Это не мнение. Это данные. Используй их или продолжай быть слабаком.
    """
    
    bot.reply_to(m, fact_msg, parse_mode="Markdown")

@bot.message_handler(commands=['мотивация'])
def send_hard_motivation(m):
    """Жёсткая мотивация"""
    motivation = random.choice(HARD_MOTIVATION)
    
    motivation_msg = f"""
💢 *ПРАВДА, КОТОРУЮ ТЫ НЕ ХОЧЕШЬ СЛЫШАТЬ* 💢

{motivation}

🏆 *ВОПРОС НА ЗАСЫПКУ:*
1. Что ты построил за последний месяц?
2. Сколько энергии потратил впустую?
3. Кем ты будешь через год, если продолжишь как сейчас?

📊 *ПРОВЕРЬ СЕБЯ:* `/стат`
👊 *ПОЛУЧИ ПРАВДУ:* `/удар`
"""
    
    bot.reply_to(m, motivation_msg, parse_mode="Markdown")

# --- ОСНОВНЫЕ КОМАНДЫ ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() in ['нофап старт', '/старт'])
def start_nofap(m):
    uid, cid, name = m.from_user.id, m.chat.id, m.from_user.first_name
    
    res = db_query("SELECT attempts, start_time FROM users WHERE id = ? AND chat_id = ?", 
                   (uid, cid), fetch=True)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not res:
        db_query("INSERT INTO users (id, chat_id, username, start_time, last_start_time, attempts, current_streak) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                 (uid, cid, name, now, now, 0, 0))
        
        welcome_msg = f"""
🚀 *ПОЕХАЛИ, {name.upper()}!* 🚀

Ты сделал первый шаг. Теперь главное — не остановиться.

📊 *ЧТО БУДЕТ, ЕСЛИ ВЫДЕРЖИШЬ:*
7 дней → тестостерон +45.7% (наука)
30 дней → мозг перезагружен (факт)
90 дней → ты другой человек (реальность)

⚠️ *ЧТО БУДЕТ, ЕСЛИ СРЫВЕШЬСЯ:*
Будешь как все. Обычный. Заурядный. Слабый.

💪 *ВЫБОР ЗА ТОБОЙ.*
"""
        bot.reply_to(m, welcome_msg, parse_mode="Markdown")
    else:
        attempts = res[0][0] + 1
        db_query("UPDATE users SET attempts = ?, last_start_time = ?, start_time = ?, current_streak = ? WHERE id = ? AND chat_id = ?", 
                 (attempts, now, now, 0, uid, cid))
        
        if attempts == 1:
            response = f"😔 {name}, первый срыв. Это ещё не провал, но уже тревожный звоночек."
        else:
            response = f"🔄 {name}, срыв №{attempts}. Паттерн слабости формируется. Разорви его."
        
        bot.reply_to(m, f"{response}\n\n🔬 Наука: `/факт`\n💢 Правда: `/удар`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == 'мой нофап')
def my_stats_simple(m):
    user_id, chat_id = m.from_user.id, m.chat.id
    
    res = db_query("SELECT start_time, attempts, username FROM users WHERE id = ? AND chat_id = ?", 
                   (user_id, chat_id), fetch=True)
    
    if not res:
        bot.reply_to(m, "❌ *Не начал.* Слабо начать? `нофап старт`", parse_mode="Markdown")
        return
    
    start_dt_str, attempts, username = res[0]
    start_dt = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_dt).days
    
    status_msg = get_user_status_message(days, attempts, username or "Аноним")
    
    simple_msg = f"""
{status_msg}

📅 Стрик: {days} дней
📉 Срывов: {attempts}
📊 Подробно: `/стат`
"""
    bot.reply_to(m, simple_msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text and m.text.lower() == 'нофап')
def reply_stats(m):
    if not m.reply_to_message:
        return bot.reply_to(m, "❌ Ответь на сообщение и напиши 'нофап'")
    
    target_user = m.reply_to_message.from_user
    user_id, chat_id = target_user.id, m.chat.id
    
    res = db_query("SELECT start_time, attempts, username FROM users WHERE id = ? AND chat_id = ?", 
                   (user_id, chat_id), fetch=True)
    
    if not res:
        bot.reply_to(m, f"❌ {target_user.first_name} ещё не начал. Видимо, слабо.", parse_mode="Markdown")
        return
    
    start_dt_str, attempts, username = res[0]
    start_dt = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_dt).days
    
    if attempts == 0 and days > 7:
        response = f"🏆 {target_user.first_name} — {days} дней без срывов. Мужик."
    elif attempts > days/2:
        response = f"⚠️ {target_user.first_name} — {days} дней, но {attempts} срывов. Нестабильно."
    else:
        response = f"📊 {target_user.first_name} — {days} дней, {attempts} срывов."
    
    bot.reply_to(m, response, parse_mode="Markdown")

# --- АВТО-ФУНКЦИИ ---
def broadcast_hard_motivation():
    """Рассылка жёсткой мотивации"""
    try:
        chats = db_query("SELECT DISTINCT chat_id FROM users", fetch=True)
        for (c_id,) in chats:
            if random.random() > 0.5:
                msg = random.choice(HARD_MOTIVATION)
            else:
                msg = random.choice(HARD_INSULTS)
            
            bot.send_message(c_id, f"💢 *ЕЖЕДНЕВНАЯ ПРАВДА:*\n\n{msg}", parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка в рассылке: {e}")

def run_scheduler():
    """Запуск планировщика"""
    schedule.every(6).hours.do(broadcast_hard_motivation)
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            print(f"Ошибка в планировщике: {e}")
            time.sleep(60)

# --- ЗАПУСК ---
if __name__ == '__main__':
    print("=" * 60)
    print("🤖 NOFAP: ЖЕСТКИЙ РЕЖИМ АКТИВИРОВАН")
    print(f"✅ Токен загружен: {'Да' if TOKEN else 'Нет'}")
    print(f"💢 Жёстких сообщений: {len(HARD_MOTIVATION) + len(HARD_INSULTS)}")
    print("=" * 60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("📅 Рассылка жёсткой правды каждые 6 часов")
    
    print("\n🔄 Бот запущен. Доступные команды:")
    print("1.  /помощь - команды")
    print("2.  /старт - начать (слабак?)")
    print("3.  /стат - статистика (правда глаза колет)")
    print("4.  /факт - наука (не мнение)")
    print("5.  /мотивация - жёсткая правда")
    print("6.  /удар - получить по шапке")
    print("7.  /топ - кто тут мужик")
    print("8.  'мой нофап' - базовая стата")
    print("9.  Ответить + 'нофап' - стата другого")
    print("-" * 60)
    print("⚡ Режим: ЖЕСТКИЙ. Без жалости. Только правда.")
    print("=" * 60)
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
