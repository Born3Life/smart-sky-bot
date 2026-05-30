from __future__ import annotations

import logging
from typing import Any

import requests

from config import openweather_api_key

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def fetch_forecast(city: str) -> list[dict[str, Any]] | None:
    """Return 7-day forecast (one entry per day at noon)."""
    api_key = openweather_api_key()
    if not api_key:
        return None

    try:
        resp = requests.get(
            FORECAST_URL,
            params={"q": city, "appid": api_key, "units": "metric", "lang": "ru"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        logger.exception("forecast fetch failed for %s", city)
        return None

    daily: dict[str, dict[str, Any]] = {}
    for entry in data.get("list", []):
        dt = entry.get("dt_txt", "")
        date = dt[:10]
        if "12:00:00" in dt or date not in daily:
            daily[date] = {
                "date": date,
                "temp": round(entry["main"]["temp"]),
                "feels_like": round(entry["main"]["feels_like"]),
                "humidity": entry["main"]["humidity"],
                "wind": round(entry["wind"]["speed"], 1),
                "desc": entry["weather"][0]["description"],
                "icon": entry["weather"][0]["icon"],
                "pressure": entry["main"]["pressure"],
                "clouds": entry["clouds"]["all"],
                "rain": (entry.get("rain") or {}).get("3h", 0),
            }

    result = list(daily.values())[:7]
    if not result:
        return None
    return result


def fmt_forecast(entries: list[dict[str, Any]]) -> str:
    lines = ["📅 <b>Прогноз на 7 дней</b>\n"]
    for e in entries:
        lines.append(
            f"▫️ <b>{e['date']}</b> — "
            f"{e['temp']}°C, {e['desc']}\n"
            f"   💧 {e['humidity']}% 💨 {e['wind']} м/с",
        )
    return "\n".join(lines)
