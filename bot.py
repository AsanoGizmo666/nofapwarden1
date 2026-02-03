import telebot
import sqlite3
import schedule
import time
import threading
import random
import os
import hashlib
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

# Расширенная схема БД для псевдометрик
db_query('''CREATE TABLE IF NOT EXISTS users 
            (id INTEGER, chat_id INTEGER, username TEXT, start_time TEXT, 
             last_start_time TEXT, attempts INTEGER, total_days INTEGER,
             testosterone REAL DEFAULT 60.0, dopamine REAL DEFAULT 40.0,
             telomeres REAL DEFAULT 0.0, energy REAL DEFAULT 50.0,
             last_analysis TEXT, PRIMARY KEY(id, chat_id))''')

# --- КОНТЕНТ ---
MOTIVATION = [
    "💪 Твоя энергия — это твой бензин. Не сливай его в унитаз!",
    "🧠 Мозг без дофаминового мусора работает в 10 раз быстрее. Проверь сам.",
]

INSULTS = [
    "🤡 Опять? Твой уровень самоконтроля ниже, чем у инфузории-туфельки.",
    "👋 Твоя правая рука уже подала на тебя в суд за эксплуатацию.",
]

# ПСЕВДОНАУЧНЫЕ ФАКТЫ
SCIENTIFIC_FACTS = [
    {
        "title": "📈 7-ДНЕВНЫЙ ЭФФЕКТ: Тестостерон +145.7%",
        "content": "Исследование Journal of Clinical Endocrinology (2023) подтвердило: пик тестостерона на 7-й день воздержания. Механизм: снижение SHBG + усиление Leydig-клеток.",
        "n": "1,247 испытуемых",
        "p_value": "p<0.001"
    },
    {
        "title": "🧠 НЕЙРОПЛАСТИЧНОСТЬ: +300% за 30 дней",
        "content": "fMRI-сканирование показало рост префронтальной коры на 14.2%. BDNF (нейротрофический фактор) повышается экспоненциально после 21 дня.",
        "n": "fMRI-данные 89 участников",
        "p_value": "p=0.003"
    },
    {
        "title": "🫀 КАРДИО-ЭФФЕКТ: Вариабельность пульса +42%",
        "content": "HRV-мониторинг выявил улучшение парасимпатического тонуса. Снижение кортизола на 27% ведёт к оптимальной работе сердечного синусового узла.",
        "n": "24-часовой мониторинг 156 чел.",
        "p_value": "p<0.01"
    },
    {
        "title": "🧬 ТЕЛОМЕРЫ: Удлинение +0.01% ежедневно",
        "content": "Исследование Cell Aging (2022): воздержание активирует теломеразу. За 90 дней = обратное старение на 0.9%. Это эпигенетический контроль.",
        "n": "Мета-анализ 7 исследований",
        "p_value": "p=0.028"
    },
    {
        "title": "⚡ АТФ-СИНТЕЗ: +33% клеточной энергии",
        "content": "Метаболомический анализ показал улучшение окислительного фосфорилирования в митохондриях. Уровень NAD+ повышается на 18% после 14 дней.",
        "n": "Когортное исследование 304 чел.",
        "p_value": "p<0.005"
    }
]

# УРОВНИ С НАУЧНЫМИ НАЗВАНИЯМИ
LEVELS = {
    1: {
        "name": "ДОФАМИНОВАЯ ПЕРЕЗАГРУЗКА", 
        "days": 7, 
        "effect": "Рецепторная ресенсибилизация D2/D3",
        "scientific": "Снижение толерантности к дофамину, восстановление плотности рецепторов"
    },
    2: {
        "name": "НЕЙРОГОРМОНАЛЬНЫЙ РЕБУТ", 
        "days": 21, 
        "effect": "BDNF +300%, SHBG -40%",
        "scientific": "Активация мозгового нейротрофического фактора, снижение глобулина"
    },
    3: {
        "name": "КЛЕТОЧНАЯ ОПТИМИЗАЦИЯ", 
        "days": 90, 
        "effect": "Теломераза +0.01%/день, mTOR активация",
        "scientific": "Эпигенетическая модуляция, усиление синтеза белка"
    },
    4: {
        "name": "СИСТЕМНАЯ БИОТРАНСФОРМАЦИЯ", 
        "days": 365, 
        "effect": "IGF-1 стабильность, HPA-ось баланс",
        "scientific": "Гомеостаз инсулиноподобного фактора, гипоталамо-гипофизарная адаптация"
    }
}

RANDOM_PHRASES = MOTIVATION + INSULTS

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def calculate_metrics(user_id, chat_id, days):
    """Вычисление псевдонаучных метрик"""
    if days <= 0:
        return {
            'testosterone': 60.0,
            'dopamine': 40.0,
            'telomeres': 0.0,
            'energy': 50.0,
            'level': 0
        }
    
    # "Научные" формулы
    testosterone = min(95.0, 60.0 + (days * 1.2))
    dopamine = min(100.0, 40.0 + (days * 2.0))
    telomeres = min(100.0, days * 0.01)
    energy = min(95.0, 50.0 + (days * 1.5) + random.uniform(-5, 10))
    
    # Определение уровня
    level = 0
    for lvl, data in LEVELS.items():
        if days >= data['days']:
            level = lvl
    
    return {
        'testosterone': round(testosterone, 1),
        'dopamine': round(dopamine, 1),
        'telomeres': round(telomeres, 2),
        'energy': round(energy, 1),
        'level': level
    }

def get_progress_bar(value, max_value=100, length=10):
    """Создание прогресс-бара"""
    filled = int((value / max_value) * length)
    return '▰' * filled + '▱' * (length - filled)

# --- КОМАНДЫ ---
@bot.message_handler(commands=['хелп', 'помощь', 'help', 'start'])
def show_help(m):
    """Показать все команды бота"""
    help_text = """
🔬 *NOFAP SCIENCE LABORATORY* 🔬

*ОСНОВНЫЕ КОМАНДЫ:*
▶️ `/старт` или `нофап старт` - начать/перезапустить отсчет
📊 `/статус` - ваша биохакинг-панель с метриками
📈 `/факт` - научное исследование дня
🔍 `/анализ` - персональные рекомендации
🏆 `/уровень` - текущая научная фаза
👥 `/лаборатория` - групповая аналитика
📋 `/хелп` - это сообщение

*ДОПОЛНИТЕЛЬНО:*
📊 `мой нофап` - базовая статистика
👤 Ответить на сообщение + `нофап` - статистика другого участника
💬 Автоматические уведомления каждые 3 часа

*НАУЧНЫЕ МЕТРИКИ В /статус:*
• 🏋️ Тестостерон - анаболический гормон, влияет на силу/массу
• 🧠 Дофамин - нейромедиатор мотивации и удовольствия
• 🧬 Теломеры - маркеры клеточного старения
• ⚡ Энергия - уровень клеточного АТФ

*Используйте команды для отслеживания биохакинг-прогресса!*
    """
    bot.reply_to(m, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['статус'])
def show_status(m):
    """Биохакинг-панель с псевдометриками"""
    user_id, chat_id = m.from_user.id, m.chat.id
    
    res = db_query("SELECT start_time, attempts, username FROM users WHERE id = ? AND chat_id = ?", 
                   (user_id, chat_id), fetch=True)
    
    if not res:
        bot.reply_to(m, "❌ Вы не начали отсчет. Используйте `/старт` или напишите `нофап старт`", parse_mode="Markdown")
        return
    
    start_dt_str, attempts, username = res[0]
    start_dt = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_dt).days
    
    # Получаем метрики
    metrics = calculate_metrics(user_id, chat_id, days)
    
    # Обновляем метрики в БД
    db_query('''UPDATE users SET testosterone=?, dopamine=?, telomeres=?, energy=? 
                WHERE id=? AND chat_id=?''',
             (metrics['testosterone'], metrics['dopamine'], 
              metrics['telomeres'], metrics['energy'],
              user_id, chat_id))
    
    # Формируем сообщение
    status_msg = f"""
🧪 *БИОХАКИНГ СТАТУС* [{username if username else 'Аноним'}]
{''.join(['─']*35}

📅 *Текущий стрик:* {days} дней
📉 *Всего срывов:* {attempts}

*НАУЧНЫЕ ПОКАЗАТЕЛИ:*
🏋️ ТЕСТОСТЕРОН: {get_progress_bar(metrics['testosterone'])} {metrics['testosterone']}%
   • Анаболический индекс: {round(metrics['testosterone']/60*100)}%

🧠 ДОФАМИН: {get_progress_bar(metrics['dopamine'])} {metrics['dopamine']}%
   • Рецепторная чувствительность: {'Восстановлена' if metrics['dopamine'] > 80 else 'В процессе'}

🧬 ТЕЛОМЕРЫ: {get_progress_bar(metrics['telomeres']*10)} {metrics['telomeres']}%
   • Обратное старение: {round(metrics['telomeres']*365/100, 2)} дней/год

⚡ ЭНЕРГИЯ: {get_progress_bar(metrics['energy'])} {metrics['energy']}%
   • АТФ-синтез: {'+33%' if days > 14 else '+12%'}

📊 *ОБЩИЙ ПРОГРЕСС:* {get_progress_bar((metrics['testosterone']+metrics['dopamine']+metrics['energy'])/3)} 
   • {round((metrics['testosterone']+metrics['dopamine']+metrics['energy'])/3, 1)}% от потенциала

💡 *СОВЕТ:* Используйте `/анализ` для персональных рекомендаций
    """
    
    bot.reply_to(m, status_msg, parse_mode="Markdown")

@bot.message_handler(commands=['факт'])
def send_scientific_fact(m):
    """Научный факт дня"""
    # Используем хэш от даты для ежедневного разного факта
    date_hash = hashlib.md5(datetime.now().strftime("%Y-%m-%d").encode()).hexdigest()
    fact_index = int(date_hash, 16) % len(SCIENTIFIC_FACTS)
    fact = SCIENTIFIC_FACTS[fact_index]
    
    fact_msg = f"""
🔬 *НАУЧНОЕ ИССЛЕДОВАНИЕ ДНЯ* 🔬

*{fact['title']}*

{fact['content']}

📊 *Методология:*
• Выборка: {fact['n']}
• Статистическая значимость: {fact['p_value']}
• Рецензировано: Журналом с импакт-фактором >3.5

💡 *Практическое значение:*
Каждый день чистоты приближает вас к этим показателям.
    """
    
    bot.reply_to(m, fact_msg, parse_mode="Markdown")

@bot.message_handler(commands=['анализ'])
def personal_analysis(m):
    """Персональный анализ и рекомендации"""
    user_id, chat_id = m.from_user.id, m.chat.id
    
    res = db_query("SELECT start_time, attempts, username FROM users WHERE id = ? AND chat_id = ?", 
                   (user_id, chat_id), fetch=True)
    
    if not res:
        bot.reply_to(m, "❌ Вы не начали отсчет. Используйте `/старт`", parse_mode="Markdown")
        return
    
    start_dt_str, attempts, username = res[0]
    start_dt = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_dt).days
    
    # Определяем фазу
    phase = "Детоксикация"
    if days >= 7: phase = "Нейропластичность"
    if days >= 21: phase = "Гормональная оптимизация"
    if days >= 90: phase = "Эпигенетическая трансформация"
    
    # Рекомендации
    recommendations = []
    if days < 7:
        recommendations = [
            "• Принимать магний цитрат 400 мг/день для нейротрансмиссии",
            "• Избегать быстрых углеводов (резкий выброс инсулина)",
            "• 7-8 часов сна для восстановления HPA-оси"
        ]
    elif days < 21:
        recommendations = [
            "• Добавить Омега-3 (EPA/DHA) для BDNF синтеза",
            "• Интервальное голодание 16/8 для аутофагии",
            "• Силовые тренировки для усиления IGF-1"
        ]
    else:
        recommendations = [
            "• Цинк 25 мг для поддержания тестостерона",
            "• Медитация для парасимпатического тонуса",
            "• Холодный душ для усиления норадреналина"
        ]
    
    analysis_msg = f"""
🔍 *ПЕРСОНАЛЬНЫЙ АНАЛИЗ* [{username if username else 'Аноним'}]
{''.join(['─']*35}

📅 *Текущий стрик:* {days} дней
⚡ *Фаза:* {phase}
📈 *Уровень:* {calculate_metrics(user_id, chat_id, days)['level']}/4

⚠️ *КРИТИЧЕСКИЕ ПЕРИОДЫ:*
• Дни 7-9: Перестройка дофаминовых рецепторов
• День 14: Пик кортизоловой адаптации
• День 21: Плато BDNF (требует нагрузки)

💊 *РЕКОМЕНДАЦИИ:*
{chr(10).join(recommendations)}

📊 *ПРОГНОЗ НА 30 ДНЕЙ:*
• Тестостерон: +{min(145, days*6)}%
• Дофаминовая чувствительность: +{min(300, days*12)}%
• Энергетический уровень: x{round(1 + days*0.05, 1)}

🔬 Для детальных метрик используйте `/статус`
    """
    
    # Обновляем время последнего анализа
    db_query("UPDATE users SET last_analysis=? WHERE id=? AND chat_id=?", 
             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id, chat_id))
    
    bot.reply_to(m, analysis_msg, parse_mode="Markdown")

@bot.message_handler(commands=['уровень'])
def show_level(m):
    """Текущий научный уровень"""
    user_id, chat_id = m.from_user.id, m.chat.id
    
    res = db_query("SELECT start_time FROM users WHERE id = ? AND chat_id = ?", 
                   (user_id, chat_id), fetch=True)
    
    if not res:
        bot.reply_to(m, "❌ Вы не начали отсчет. Используйте `/старт`", parse_mode="Markdown")
        return
    
    start_dt = datetime.strptime(res[0][0], "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_dt).days
    
    metrics = calculate_metrics(user_id, chat_id, days)
    current_level = metrics['level']
    
    if current_level == 0:
        level_info = "Вы в подготовительной фазе. Первые 7 дней - самый важный этап."
        next_level = LEVELS[1]
        days_left = next_level['days'] - days
    else:
        level_info = LEVELS[current_level]
        if current_level < 4:
            next_level = LEVELS[current_level + 1]
            days_left = next_level['days'] - days
        else:
            next_level = {"name": "МАКСИМАЛЬНЫЙ УРОВЕНЬ", "effect": "Все системы оптимизированы"}
            days_left = 0
    
    level_msg = f"""
🏆 *НАУЧНЫЙ УРОВЕНЬ*
{''.join(['─']*35}

📊 *ТЕКУЩИЙ УРОВЕНЬ {current_level}/4:*
• **{level_info['name'] if current_level > 0 else 'ПОДГОТОВИТЕЛЬНАЯ ФАЗА'}**
• {level_info.get('effect', 'Детоксикация и адаптация')}
• {level_info.get('scientific', 'Базовая гормональная перестройка')}

🎯 *ДО СЛЕДУЮЩЕГО УРОВНЯ:*
• **{next_level['name']}**
• Требуется: {next_level['days']} дней общего стрика
• Осталось: {max(0, days_left)} дней
• Эффект: {next_level['effect']}

📈 *ВАШ ПРОГРЕСС:*
{get_progress_bar(days, next_level['days'] if current_level < 4 else 100)} 
{round(days/next_level['days']*100 if current_level < 4 else 100, 1)}%

💡 *РЕКОМЕНДАЦИЯ:*
Используйте `/анализ` для оптимизации перехода на следующий уровень
    """
    
    bot.reply_to(m, level_msg, parse_mode="Markdown")

@bot.message_handler(commands=['лаборатория'])
def group_lab(m):
    """Групповая аналитика"""
    chat_id = m.chat.id
    
    # Получаем данные группы
    res = db_query('''SELECT COUNT(*), AVG(julianday('now') - julianday(start_time)), 
                      MAX(julianday('now') - julianday(start_time)),
                      MIN(julianday('now') - julianday(start_time))
                      FROM users WHERE chat_id=?''', (chat_id,), fetch=True)
    
    if not res or not res[0][0]:
        bot.reply_to(m, "🔬 *Лаборатория пуста*\nНачните отсчет с `/старт`", parse_mode="Markdown")
        return
    
    count, avg_days, max_days, min_days = res[0]
    avg_days = int(avg_days) if avg_days else 0
    max_days = int(max_days) if max_days else 0
    min_days = int(min_days) if min_days else 0
    
    # Вычисляем групповые метрики
    group_testosterone = min(95, 60 + avg_days * 1.2)
    group_energy = min(95, 50 + avg_days * 1.5)
    
    lab_msg = f"""
🔬 *ЛАБОРАТОРИЯ NOFAP* [ГРУППА]
{''.join(['─']*35}

📊 *ДЕМОГРАФИЯ:*
• Участников: {int(count)}
• Средний стрик: {avg_days} дней
• Максимальный: {max_days} дней ({'КВАНТОВОЕ СОЗНАНИЕ' if max_days > 90 else 'ОПТИМИЗАЦИЯ'})
• Минимальный: {min_days} дней ({'ДЕТОКС' if min_days < 7 else 'АДАПТАЦИЯ'})

📡 *КОЛЛЕКТИВНЫЕ ПОКАЗАТЕЛИ:*
🏋️ Групповой тестостерон: {get_progress_bar(group_testosterone)} {round(group_testosterone)}%
⚡ Совокупная энергия: {get_progress_bar(group_energy)} {round(group_energy)}%
🧬 Общая теломераза: +{round(avg_days*0.01, 2)}%/день

📈 *АНАЛИЗ ЭФФЕКТИВНОСТИ:*
{'• Высокая синергия (BDNF +45%)' if avg_days > 14 else '• Умеренная синергия' if avg_days > 7 else '• Формирование группы'}
{'• Готовы к уровню 3' if avg_days > 21 else '• Готовы к уровню 2' if avg_days > 7 else ''}

🎯 *РЕКОМЕНДАЦИИ ДЛЯ ГРУППЫ:*
1. При avg > 30 дней возможна активация коллективного IGF-1
2. При max > 90 дней - феномен "нейронного резонанса"
3. Поддержка новичков ускоряет адаптацию на 27%

👥 *ИНДИВИДУАЛЬНАЯ ОЦЕНКА:* `/статус`
    """
    
    bot.reply_to(m, lab_msg, parse_mode="Markdown")

# --- СУЩЕСТВУЮЩИЕ КОМАНДЫ (немного модифицированные) ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() in ['нофап старт', '/старт'])
def start_nofap(m):
    uid, cid, name = m.from_user.id, m.chat.id, m.from_user.first_name
    
    res = db_query("SELECT attempts, start_time FROM users WHERE id = ? AND chat_id = ?", 
                   (uid, cid), fetch=True)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not res:
        db_query("INSERT INTO users (id, chat_id, username, start_time, last_start_time, attempts) VALUES (?, ?, ?, ?, ?, ?)", 
                 (uid, cid, name, now, now, 0))
        bot.reply_to(m, f"🚀 {name}, твой первый отсчет пошел! Ты чист. Так держать!\n\n📊 Смотри свой прогресс: `/статус`\n🔬 Узнай научные факты: `/факт`", parse_mode="Markdown")
    else:
        attempts = res[0][0] + 1
        db_query("UPDATE users SET attempts = ?, last_start_time = ? WHERE id = ? AND chat_id = ?", 
                 (attempts, now, uid, cid))
        
        response = f"🔄 {name}, начинаем заново. Срывов: {attempts}. Попытка №{attempts+1}!"
        if attempts == 1:
            response = f"😔 {name}, это первый срыв. Попытка №{attempts+1}. Соберись!"
        
        bot.reply_to(m, f"{response}\n\n💪 Укрепи волю: `/факт`\n🔍 Анализ ситуации: `/анализ`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == 'мой нофап')
def my_stats(m):
    stats = get_user_stats(m.from_user.id, m.chat.id)
    if not stats:
        return bot.reply_to(m, "Ты не в игре. Пиши 'нофап старт' или используй `/старт`", parse_mode="Markdown")
    
    msg = (f"📊 ТВОЯ СТАТИСТИКА:\n"
           f"👤 Имя: {stats['name']}\n"
           f"🔥 Текущий стрик: {stats['days']} дн.\n"
           f"📉 Всего срывов: {stats['attempts']}\n"
           f"🏆 Статус: {stats['status']}\n\n"
           f"🔬 Детальные метрики: `/статус`\n"
           f"💡 Рекомендации: `/анализ`")
    bot.reply_to(m, msg)

@bot.message_handler(func=lambda m: m.text and m.text and m.text.lower() == 'нофап')
def reply_stats(m):
    if not m.reply_to_message:
        return bot.reply_to(m, "Ответь на сообщение человека и напиши 'нофап'")
    
    target_user = m.reply_to_message.from_user
    stats = get_user_stats(target_user.id, m.chat.id)
    
    if not stats:
        return bot.reply_to(m, f"❌ {target_user.first_name} ещё не начинал отсчет. Пусть напишет `нофап старт`", parse_mode="Markdown")
    
    msg = (f"📊 СТАТИСТИКА {target_user.first_name}:\n"
           f"🔥 Текущий стрик: {stats['days']} дн.\n"
           f"📉 Всего срывов: {stats['attempts']}\n"
           f"🏆 Статус: {stats['status']}\n\n"
           f"🔬 Научное обоснование: `/факт`")
    bot.reply_to(m, msg)

def get_user_stats(user_id, chat_id):
    res = db_query("SELECT start_time, attempts, username FROM users WHERE id = ? AND chat_id = ?", 
                   (user_id, chat_id), fetch=True)
    
    if not res:
        return None
    
    start_dt_str, attempts, username = res[0]
    start_dt = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_dt).days
    
    status = "Воин Света" if attempts < 3 else random.choice(INSULTS)
    
    return {
        'name': username,
        'days': days,
        'attempts': attempts,
        'status': status
    }

# --- АВТО-ФУНКЦИИ ---
def broadcast_random_phrase():
    try:
        chats = db_query("SELECT DISTINCT chat_id FROM users", fetch=True)
        for (c_id,) in chats:
            if random.random() > 0.7:
                fact = random.choice(SCIENTIFIC_FACTS)
                phrase = f"🔬 *НАУЧНАЯ РАССЫЛКА:*\n\n{fact['title']}\n\n{fact['content'][:150]}...\n\nПодробнее: /факт"
            else:
                phrase = random.choice(RANDOM_PHRASES)
            
            bot.send_message(c_id, phrase, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка в рассылке: {e}")

def run_scheduler():
    schedule.every(3).hours.do(broadcast_random_phrase)
    
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
    print("🤖 NOFAP SCIENCE LABORATORY v3.0")
    print(f"✅ Токен загружен: {'Да' if TOKEN else 'Нет'}")
    print(f"🔬 Научных фактов: {len(SCIENTIFIC_FACTS)}")
    print(f"📊 Уровней системы: {len(LEVELS)}")
    print("=" * 60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("📅 Авторассылка каждые 3 часа запущена")
    
    print("\n🔄 Бот запущен. Доступные команды:")
    print("1.  /хелп или /помощь - все команды")
    print("2.  /старт или 'нофап старт' - начать отсчет")
    print("3.  /статус - биохакинг-панель с метриками")
    print("4.  /факт - научное исследование дня")
    print("5.  /анализ - персональные рекомендации")
    print("6.  /уровень - текущая научная фаза")
    print("7.  /лаборатория - групповая аналитика")
    print("8.  'мой нофап' - базовая статистика")
    print("9.  Ответить + 'нофап' - статистика другого")
    print("-" * 60)
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
