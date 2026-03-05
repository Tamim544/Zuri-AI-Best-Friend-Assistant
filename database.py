import sqlite3
import json
import os
import uuid
import os

DB_PATH = "chatbot_memory.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL DEFAULT 'default_user',
            title      TEXT NOT NULL DEFAULT 'New Chat',
            history    TEXT NOT NULL DEFAULT '[]',
            context    TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

def load_history(session_id: str, user_id: str = "default_user") -> tuple[list[dict], str]:
    conn = sqlite3.connect(DB_PATH)
    # Ensure session exists
    conn.execute("INSERT OR IGNORE INTO sessions (session_id, user_id) VALUES (?, ?)", (session_id, user_id))
    conn.commit()

    row = conn.execute(
        "SELECT history, context FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    
    if row:
        history = json.loads(row[0]) if row[0] else []
        context = row[1] if row[1] else ""
        return history, context
    return [], ""

def save_history(session_id: str, history: list[dict], title: str = None, user_id: str = "default_user"):
    conn = sqlite3.connect(DB_PATH)
    if title:
        conn.execute("""
            INSERT INTO sessions (session_id, user_id, history, title, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET 
                history = excluded.history,
                title = excluded.title,
                updated_at = excluded.updated_at
        """, (session_id, user_id, json.dumps(history), title))
    else:
        conn.execute("""
            INSERT INTO sessions (session_id, user_id, history, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET 
                history = excluded.history,
                updated_at = excluded.updated_at
        """, (session_id, user_id, json.dumps(history)))
    conn.commit()
    conn.close()

def append_context(session_id: str, new_text: str, user_id: str = "default_user"):
    conn = sqlite3.connect(DB_PATH)
    # Ensure session exists
    conn.execute("INSERT OR IGNORE INTO sessions (session_id, user_id) VALUES (?, ?)", (session_id, user_id))
    conn.commit()
    
    current_context = conn.execute("SELECT context FROM sessions WHERE session_id=?", (session_id,)).fetchone()[0]
    updated_context = current_context + "\n\n" + new_text if current_context else new_text
    
    conn.execute("UPDATE sessions SET context = ? WHERE session_id = ?", (updated_context, session_id))
    conn.commit()
    conn.close()
def get_user_chats(user_id: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT session_id, title, updated_at FROM sessions WHERE user_id = ? ORDER BY updated_at DESC", 
        (user_id,)
    ).fetchall()
    conn.close()
    
    chats = []
    for row in rows:
        chats.append({
            "session_id": row[0],
            "title": row[1],
            "updated_at": row[2]
        })
    return chats
def clear_history(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def register_user(username: str, password_hash: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    try:
        user_id = "user_" + str(uuid.uuid4()).replace("-", "")[:12]
        conn.execute("INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)", (user_id, username, password_hash))
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None # Username exists
    finally:
        conn.close()

def get_user_by_username(username: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "password_hash": row[2]}
    return None
