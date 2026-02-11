import sqlite3
from datetime import datetime

DB_NAME = "data.db"

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            chat_id INTEGER,
            name TEXT,
            start_date TEXT,
            best_streak INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS relapses (
            user_id INTEGER,
            chat_id INTEGER,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

def start_or_relapse(uid, chat_id, name):
    """Начало нового пути или фиксация срыва"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("SELECT * FROM users WHERE user_id=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone()
    if row:
        # Уже есть пользователь — фиксируем срыв
        add_relapse(uid, chat_id)
        c.execute("UPDATE users SET start_date=? WHERE user_id=? AND chat_id=?", (now, uid, chat_id))
        conn.commit()
        conn.close()
        return "relapse", 0
    else:
        # Новый пользователь
        c.execute("INSERT INTO users (user_id, chat_id, name, start_date) VALUES (?, ?, ?, ?)",
                  (uid, chat_id, name, now))
        conn.commit()
        conn.close()
        return "start", 1

def get_stats(uid, chat_id):
    """Возвращает статистику пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT start_date FROM users WHERE user_id=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    start_date = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_date).days

    c.execute("SELECT COUNT(*) FROM relapses WHERE user_id=? AND chat_id=?", (uid, chat_id))
    relapses = c.fetchone()[0]

    # для простоты пока best = дней без срыва
    best = days - relapses

    conn.close()
    return {"days": days, "relapses": relapses, "best": best}

def top_users(chat_id):
    """Возвращает топ пользователей в чате"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, start_date, (SELECT COUNT(*) FROM relapses r WHERE r.user_id=u.user_id) FROM users u WHERE chat_id=?",
              (chat_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_relapse(uid, chat_id):
    """Фиксирует срыв пользователя"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO relapses (user_id, chat_id, date) VALUES (?, ?, ?)", (uid, chat_id, now))
    conn.commit()
    conn.close()
