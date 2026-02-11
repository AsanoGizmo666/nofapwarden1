import sqlite3
from datetime import datetime

DB_FILE = "nofap.db"

# ------------------ ИНИЦИАЛИЗАЦИЯ БД ------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Таблица пользователей
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER,
            chat_id INTEGER,
            name TEXT,
            start_date TEXT,
            relapses INTEGER DEFAULT 0,
            PRIMARY KEY (uid, chat_id)
        )
    """)
    # Таблица ачивок
    c.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            uid INTEGER,
            chat_id INTEGER,
            title TEXT,
            PRIMARY KEY (uid, chat_id, title)
        )
    """)
    # Таблица XP
    c.execute("""
        CREATE TABLE IF NOT EXISTS xp (
            uid INTEGER,
            chat_id INTEGER,
            xp INTEGER DEFAULT 0,
            PRIMARY KEY (uid, chat_id)
        )
    """)
    # Таблица активности для молчунов
    c.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            uid INTEGER,
            chat_id INTEGER,
            last_activity TEXT,
            PRIMARY KEY (uid, chat_id)
        )
    """)
    conn.commit()
    conn.close()

# ------------------ СТАРТ ИЛИ СРИВ ------------------
def start_or_relapse(uid, chat_id, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT start_date, relapses FROM users WHERE uid=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone()
    if not row:
        # новый пользователь
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO users (uid, chat_id, name, start_date) VALUES (?, ?, ?, ?)",
                  (uid, chat_id, name, now))
        conn.commit()
        conn.close()
        return "start", 1
    else:
        # пользователь уже есть
        start_date, relapses = row
        days = (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")).days
        add_relapse(uid, chat_id)
        conn.close()
        return "relapse", days

def add_relapse(uid, chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET relapses = relapses + 1 WHERE uid=? AND chat_id=?", (uid, chat_id))
    c.execute("UPDATE users SET start_date=? WHERE uid=? AND chat_id=?",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid, chat_id))
    conn.commit()
    conn.close()

# ------------------ СТАТА ------------------
def get_stats(uid, chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT start_date, relapses FROM users WHERE uid=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    start_date, relapses = row
    days = (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")).days
    best = days  # упрощено
    conn.close()
    return {"days": days, "relapses": relapses, "best": best}

# ------------------ ТОП ------------------
def top_users(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, start_date, relapses FROM users WHERE chat_id=?", (chat_id,))
    users = c.fetchall()
    conn.close()
    return users

# ------------------ ПОСЛЕДНИЕ СРЫВЫ ------------------
def get_last_relapses(chat_id, limit=5):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, start_date FROM users WHERE chat_id=? ORDER BY start_date DESC LIMIT ?", (chat_id, limit))
    rows = c.fetchall()
    result = []
    for name, start_date in rows:
        days = (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")).days
        result.append((name, days))
    conn.close()
    return result

# ------------------ АКТИВНОСТЬ ------------------
def get_user_last_activity(uid, chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT last_activity FROM activity WHERE uid=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    return None

# ------------------ ВСЕ ПОЛЬЗОВАТЕЛИ ------------------
def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT uid, name, chat_id, start_date, relapses FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

# ------------------ АЧИВКИ ------------------
def add_achievement(uid, chat_id, title):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO achievements (uid, chat_id, title) VALUES (?, ?, ?)", (uid, chat_id, title))
    conn.commit()
    conn.close()

def get_achievements(uid, chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title FROM achievements WHERE uid=? AND chat_id=?", (uid, chat_id))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

# ------------------ XP ------------------
def add_xp(uid, chat_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO xp (uid, chat_id, xp) VALUES (?, ?, 0)", (uid, chat_id))
    c.execute("UPDATE xp SET xp = xp + ? WHERE uid=? AND chat_id=?", (amount, uid, chat_id))
    conn.commit()
    conn.close()

def get_xp(uid, chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT xp FROM xp WHERE uid=? AND chat_id=?", (uid, chat_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0
