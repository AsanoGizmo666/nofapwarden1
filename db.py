import sqlite3
from datetime import datetime

DB_NAME = "bot.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            start_time TEXT,
            relapses INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, chat_id)
        )
        """)
        conn.commit()


def get_user(user_id, chat_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=? AND chat_id=?",
                  (user_id, chat_id))
        return c.fetchone()


def start_or_relapse(user_id, chat_id, username):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        user = get_user(user_id, chat_id)

        if not user:
            c.execute("""
            INSERT INTO users (user_id, chat_id, username, start_time)
            VALUES (?, ?, ?, ?)
            """, (user_id, chat_id, username, now))
            conn.commit()
            return "start", 0

        else:
            start_time = datetime.strptime(user[3], "%Y-%m-%d %H:%M:%S")
            days = (datetime.now() - start_time).days

            best = max(days, user[5])

            c.execute("""
            UPDATE users
            SET start_time=?, relapses=relapses+1, best_streak=?
            WHERE user_id=? AND chat_id=?
            """, (now, best, user_id, chat_id))
            conn.commit()
            return "relapse", days


def get_stats(user_id, chat_id):
    user = get_user(user_id, chat_id)
    if not user:
        return None

    start_time = datetime.strptime(user[3], "%Y-%m-%d %H:%M:%S")
    days = (datetime.now() - start_time).days

    return {
        "days": days,
        "relapses": user[4],
        "best": user[5]
    }


def top_users(chat_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
        SELECT username, start_time, relapses
        FROM users
        WHERE chat_id=?
        """, (chat_id,))
        return c.fetchall()
