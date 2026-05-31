from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from aiogram import Bot

from database import (
    conn,
    mark_briefing_sent,
    was_briefing_sent_today,
)
from services.weather_forecast import fetch_day_night, fetch_raw_forecast, fmt_day_night
from weather import fetch_by_city

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
    old_today = _today_entries(old)
    new_today = _today_entries(new)

    changes: list[str] = []

    for ne in new_today:
        n_date = ne.get("date", "")
        oe = next((o for o in old_today if o.get("date") == n_date), None)

        if oe is None:
            changes.append(f"📅 {n_date}: появился прогноз")
            continue

        old_rain = oe.get("rain", 0) or 0
        new_rain = ne.get("rain", 0) or 0
        old_snow = oe.get("snow", 0) or 0
        new_snow = ne.get("snow", 0) or 0
        old_temp = oe.get("temp")
        new_temp = ne.get("temp")

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


def _check_imminent_precipitation(city: str) -> str | None:
    """Check next 6 hours for rain/snow. Return alert text or None."""
    raw = fetch_raw_forecast(city)
    if not raw:
        return None

    alerts: list[str] = []
    for entry in raw:
        rain = entry.get("rain", 0) or 0
        snow = entry.get("snow", 0) or 0
        wind = entry.get("wind", 0) or 0
        dt_txt = entry.get("dt_txt", "")
        hour_str = dt_txt[11:16] if len(dt_txt) > 15 else ""

        if rain > 0 and rain < 5:
            alerts.append(f"🌧 В {hour_str} ожидается дождь ({rain:.1f} мм/3ч)")
        elif rain >= 5:
            alerts.append(f"⚠️ В {hour_str} сильный дождь ({rain:.1f} мм/3ч)")

        if snow > 0:
            alerts.append(f"❄️ В {hour_str} ожидается снег ({snow:.1f} мм/3ч)")

        if wind > 12:
            alerts.append(f"💨 В {hour_str} усиление ветра до {wind:.0f} м/с")

    if not alerts:
        return None

    text = "🔔 <b>Ближайшие часы</b>\n" + "\n".join(alerts[:3])
    text += "\n\n💎 <a href='/subscribe'>Полный прогноз + AI-совет в Premium</a>"
    return text


async def morning_briefing(bot: Bot) -> None:
    """Send morning briefing at ~8 AM local time."""
    now = datetime.utcnow()
    if now.hour not in (5, 6, 7, 8):
        return
    target_offset = 5  # 5 UTC = 8 MSK

    rows = conn().execute(
        "SELECT user_id, city FROM users WHERE city IS NOT NULL AND is_active = 1 AND is_premium = 1 AND notifications_enabled = 1",
    ).fetchall()

    for row in rows:
        user_id = row["user_id"]
        city = row["city"]

        if was_briefing_sent_today(user_id):
            continue

        weather = fetch_by_city(city)
        if weather is None:
            continue

        dn = fetch_day_night(city)

        text = (
            f"🌅 <b>Доброе утро!</b>\n"
            f"Сегодня в {city}:\n"
            f"📝 {weather.description.capitalize()}, {weather.temperature}°C\n"
        )
        dn_line = fmt_day_night(dn, "today")
        if dn_line:
            text += dn_line + "\n"

        text += (
            "\n🤖 <b>Персональный AI-совет</b> на сегодня — в Premium\n"
            "📅 Прогноз на 7 дней — Premium\n"
            "🔔 Такие рассылки каждый день — Premium\n\n"
            "💎 <a href='/subscribe'>Оформить Premium</a> — 50⭐/мес"
        )

        try:
            await bot.send_message(user_id, text)
            mark_briefing_sent(user_id)
            logger.info("briefing sent to %d", user_id)
        except Exception:
            logger.warning("briefing failed for %d", user_id)


async def check_and_notify(bot: Bot) -> None:
    """Check forecasts for all users and notify on changes + imminent weather."""
    rows = (
        conn()
        .execute(
            "SELECT user_id, city FROM users WHERE city IS NOT NULL AND is_active = 1 AND is_premium = 1",
        )
        .fetchall()
    )

    for row in rows:
        user_id = row["user_id"]
        city = row["city"]

        # ── Smart alerts for upcoming precipitation ──
        alert = _check_imminent_precipitation(city)
        if alert:
            try:
                await bot.send_message(user_id, alert)
            except Exception:
                logger.warning("alert failed for %d", user_id)

        # ── Forecast change detection (existing) ──
        cached = _get_cached(user_id)
        if cached and cached.get("city") != city:
            cached = None

        from services.weather_forecast import fetch_forecast

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
                logger.warning("change notification failed for %d", user_id)

        _save_cache(user_id, city, new_forecast)
