import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, id);

CREATE TABLE IF NOT EXISTS preferences (
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);
"""


def init_db():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def add_message(user_id: int, role: str, content: str):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, datetime.now(timezone.utc).isoformat()),
        )


def recent_messages(user_id: int, limit: int = 20):
    """가장 최근 대화 limit개를 시간순(오래된 -> 최신)으로 반환한다."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def set_preference(user_id: int, key: str, value: str):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO preferences (user_id, key, value, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (user_id, key, value, datetime.now(timezone.utc).isoformat()),
        )


def get_preferences(user_id: int) -> dict:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchall()
    return dict(rows)
