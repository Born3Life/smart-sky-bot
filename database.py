from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

from models import UserDict

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "smart_sky.db"


def _get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


_conn: sqlite3.Connection | None = None


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = _get_conn()
    return _conn


@contextmanager
def tx() -> Generator[sqlite3.Cursor, None, None]:
    c = conn().cursor()
    try:
        yield c
        conn().commit()
    except Exception:
        conn().rollback()
        raise
    finally:
        c.close()


def init_db() -> None:
    with tx() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                profile_type TEXT NOT NULL DEFAULT 'Обычный',
                city TEXT,
                city_lat REAL,
                city_lon REAL,
                registered_at TEXT NOT NULL DEFAULT (datetime('now')),
                is_active INTEGER DEFAULT 1,
                is_premium INTEGER DEFAULT 0,
                premium_until TEXT,
                referred_by INTEGER,
                referral_code TEXT UNIQUE,
                notifications_enabled INTEGER DEFAULT 1,
                notify_time TEXT DEFAULT '08:00',
                language TEXT DEFAULT 'ru',
                workplace TEXT DEFAULT '',
                has_children INTEGER DEFAULT 0,
                FOREIGN KEY (referred_by) REFERENCES users(user_id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS message_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_city ON users(city)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_premium ON users(is_premium)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_msg_user ON message_history(user_id, created_at)")
        logger.info("database ready at %s", DB_PATH)
    _migrate_add_columns()


def _migrate_add_columns() -> None:
    """Add missing columns for existing databases."""
    for col, col_type in [
        ("workplace", "TEXT DEFAULT ''"),
        ("has_children", "INTEGER DEFAULT 0"),
    ]:
        try:
            with tx() as c:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # column already exists


def upsert_user(user_id: int, username: str | None, full_name: str) -> bool:
    with tx() as c:
        existing = c.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if existing:
            c.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username, full_name, user_id),
            )
            return False
        c.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name),
        )
        return True


def get_user(user_id: int) -> UserDict | None:
    with tx() as c:
        row = c.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)  # type: ignore[return-value]


def update_profile(user_id: int, profile_type: str) -> None:
    with tx() as c:
        c.execute(
            "UPDATE users SET profile_type = ? WHERE user_id = ?",
            (profile_type, user_id),
        )


def update_city(
    user_id: int,
    city: str,
    lat: float | None = None,
    lon: float | None = None,
) -> None:
    with tx() as c:
        c.execute(
            "UPDATE users SET city = ?, city_lat = ?, city_lon = ? WHERE user_id = ?",
            (city, lat, lon, user_id),
        )


async def init_db_async() -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, init_db)


async def upsert_user_async(
    user_id: int,
    username: str | None,
    full_name: str,
) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, upsert_user, user_id, username, full_name)


async def get_user_async(user_id: int) -> UserDict | None:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_user, user_id)


async def update_profile_async(user_id: int, profile_type: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, update_profile, user_id, profile_type)


async def update_city_async(
    user_id: int,
    city: str,
    lat: float | None = None,
    lon: float | None = None,
) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, update_city, user_id, city, lat, lon)


def update_profile_fields(user_id: int, **fields: str | int) -> None:
    """Update arbitrary user profile fields."""
    if not fields:
        return
    pairs = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [user_id]
    with tx() as c:
        c.execute(f"UPDATE users SET {pairs} WHERE user_id = ?", vals)


async def update_profile_fields_async(user_id: int, **fields: str | int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, update_profile_fields, user_id, **fields)


def _activate_trial(user_id: int) -> bool:
    """Activate 7-day trial. Returns True if trial was just activated."""
    with tx() as c:
        row = c.execute(
            "SELECT is_premium, premium_until FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return False
        if row["is_premium"] and row["premium_until"]:
            try:
                until = datetime.fromisoformat(row["premium_until"])
                if datetime.utcnow() < until:
                    return False  # already active premium
            except (ValueError, TypeError):
                pass
        until = (datetime.utcnow() + timedelta(days=7)).isoformat()
        c.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
            (until, user_id),
        )
        return True


def _set_premium(user_id: int, days: int) -> None:
    until = (datetime.utcnow() + timedelta(days=days)).isoformat()
    with tx() as c:
        c.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
            (until, user_id),
        )


async def activate_trial_async(user_id: int) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _activate_trial, user_id)


async def set_premium_async(user_id: int, days: int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _set_premium, user_id, days)


# ── Message history (last 300 per user) ──

def add_message(user_id: int, role: str, text: str) -> None:
    """Store a message in history; keep only last 300 per user."""
    with tx() as c:
        c.execute(
            "INSERT INTO message_history (user_id, role, text) VALUES (?, ?, ?)",
            (user_id, role, text),
        )
        # Delete older messages exceeding 300
        c.execute(
            """
            DELETE FROM message_history
            WHERE id IN (
                SELECT id FROM message_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT -1 OFFSET 300
            )
            """,
            (user_id,),
        )


def get_history(user_id: int, limit: int = 300) -> list[dict[str, str]]:
    """Return last `limit` messages for a user, oldest first."""
    with tx() as c:
        rows = c.execute(
            """
            SELECT role, text FROM message_history
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        ).fetchall()
    return [{"role": r["role"], "text": r["text"]} for r in rows[-limit:]]


async def add_message_async(user_id: int, role: str, text: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, add_message, user_id, role, text)


async def get_history_async(user_id: int, limit: int = 300) -> list[dict[str, str]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_history, user_id, limit)
