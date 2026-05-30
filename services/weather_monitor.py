from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from aiogram import Bot

from database import conn
from services.weather_forecast import fetch_forecast

logger = logging.getLogger(__name__)


def _init_cache_table() -> None:
    conn().execute("""
        CREATE TABLE IF NOT EXISTS forecast_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            city TEXT NOT NULL,
            forecast_json TEXT NOT NULL,
            checked_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    conn().execute("""
        CREATE INDEX IF NOT EXISTS idx_forecast_cache_user
        ON forecast_cache(user_id)
    """)
    conn().commit()


def _get_cached(user_id: int) -> dict[str, Any] | None:
    row = (
        conn()
        .execute(
            "SELECT forecast_json FROM forecast_cache WHERE user_id = ?",
            (user_id,),
        )
        .fetchone()
    )
    if row is None:
        return None
    try:
        return json.loads(row["forecast_json"])
    except (json.JSONDecodeError, TypeError):
        return None


def _save_cache(user_id: int, city: str, forecast: list[dict[str, Any]]) -> None:
    conn().execute(
        """INSERT INTO forecast_cache (user_id, city, forecast_json, checked_at)
           VALUES (?, ?, ?, datetime('now'))
           ON CONFLICT(user_id) DO UPDATE SET
               city = excluded.city,
               forecast_json = excluded.forecast_json,
               checked_at = excluded.checked_at""",
        (user_id, city, json.dumps(forecast, ensure_ascii=False)),
    )
    conn().commit()


def _today_entries(forecast: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return [e for e in forecast if e.get("date") == today]


def _detect_changes(
    old: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> str | None:
    """Compare today's forecast entries. Return human-readable diff or None."""
    old_today = _today_entries(old)
    new_today = _today_entries(new)

    changes: list[str] = []

    for ne in new_today:
        n_date = ne.get("date", "")
        oe = next((o for o in old_today if o.get("date") == n_date), None)

        if oe is None:
            changes.append(f"📅 {n_date}: появился прогноз")
            continue

        def _get(e: dict[str, Any], k: str) -> Any:
            return e.get(k)

        old_rain = _get(oe, "rain") or 0
        new_rain = _get(ne, "rain") or 0
        old_snow = _get(oe, "snow") or 0
        new_snow = _get(ne, "snow") or 0
        old_temp = _get(oe, "temp")
        new_temp = _get(ne, "temp")

        if old_temp is not None and new_temp is not None:
            diff = abs(new_temp - old_temp)
            if diff > 5:
                changes.append(
                    f"🌡 Температура изменилась на {diff:.0f}°C "
                    f"(было {old_temp}°C, стало {new_temp}°C)"
                )

        if old_rain == 0 and new_rain > 0:
            changes.append(f"🌧 Ожидается дождь ({new_rain:.1f} мм)")
        elif old_rain > 0 and new_rain == 0:
            changes.append("✅ Дождь больше не ожидается")

        if old_snow == 0 and new_snow > 0:
            changes.append(f"❄️ Ожидается снег ({new_snow:.1f} мм)")
        elif old_snow > 0 and new_snow == 0:
            changes.append("✅ Снег больше не ожидается")

    if not changes:
        return None

    return "⚠️ <b>Прогноз изменился!</b>\n\n" + "\n".join(changes)


async def check_and_notify(bot: Bot) -> None:
    """Check forecasts for all users and notify on changes."""
    rows = (
        conn()
        .execute(
            "SELECT user_id, city FROM users WHERE city IS NOT NULL AND is_active = 1",
        )
        .fetchall()
    )

    for row in rows:
        user_id = row["user_id"]
        city = row["city"]

        cached = _get_cached(user_id)
        if cached and cached.get("city") != city:
            cached = None

        new_forecast = fetch_forecast(city)
        if new_forecast is None:
            continue

        if cached is None:
            _save_cache(user_id, city, new_forecast)
            continue

        old_forecast = cached.get("forecast", [])
        if not old_forecast:
            continue

        diff = _detect_changes(old_forecast, new_forecast)
        if diff:
            try:
                await bot.send_message(user_id, diff)
            except Exception:
                logger.warning("failed to notify user %d", user_id)

        _save_cache(user_id, city, new_forecast)
