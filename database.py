from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import contextmanager
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
                FOREIGN KEY (referred_by) REFERENCES users(user_id)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_city ON users(city)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_premium ON users(is_premium)")
        logger.info("database ready at %s", DB_PATH)


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
