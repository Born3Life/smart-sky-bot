from __future__ import annotations

import logging
from datetime import datetime, timedelta
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
                "snow": (entry.get("snow") or {}).get("3h", 0),
            }

    result = list(daily.values())[:7]
    if not result:
        return None
    return result


def fetch_raw_forecast(city: str) -> list[dict[str, Any]] | None:
    """Return raw 3-hour forecast entries (next 24h by default)."""
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
        logger.exception("raw forecast fetch failed for %s", city)
        return None

    entries: list[dict[str, Any]] = []
    for entry in data.get("list", [])[:8]:  # next ~24h
        entries.append(
            {
                "dt_txt": entry["dt_txt"],
                "temp": round(entry["main"]["temp"]),
                "wind": round(entry["wind"]["speed"], 1),
                "desc": entry["weather"][0]["description"],
                "rain": (entry.get("rain") or {}).get("3h", 0),
                "snow": (entry.get("snow") or {}).get("3h", 0),
            }
        )
    return entries


def fetch_day_night(city: str) -> dict[str, Any] | None:
    """Extract day (06-18) and night (18-06) temp ranges from 3-hour forecast."""
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
        logger.exception("day/night fetch failed for %s", city)
        return None

    result: dict[str, Any] = {}
    dates_seen: set[str] = set()

    for entry in data.get("list", []):
        dt = entry.get("dt_txt", "")
        date_part = dt[:10]
        if date_part in dates_seen:
            continue
        dates_seen.add(date_part)

        day_temps: list[float] = []
        night_temps: list[float] = []
        for e2 in data.get("list", []):
            if e2.get("dt_txt", "")[:10] != date_part:
                continue
            temp = e2["main"]["temp"]
            hour = int(e2["dt_txt"][11:13]) if len(e2.get("dt_txt", "")) > 13 else 0
            if 6 <= hour < 18:
                day_temps.append(temp)
            else:
                night_temps.append(temp)

        day_info: dict[str, Any] = {}
        if day_temps:
            day_info["day_high"] = round(max(day_temps))
            day_info["day_low"] = round(min(day_temps))
        if night_temps:
            night_info: dict[str, Any] = {}
            night_info["night_high"] = round(max(night_temps))
            night_info["night_low"] = round(min(night_temps))
            day_info.update(night_info)
        if day_info:
            result[date_part] = day_info

    today = datetime.utcnow().strftime("%Y-%m-%d")
    tomorrow = (datetime.utcnow().replace(hour=0, minute=0, second=0) + timedelta(days=1)).strftime("%Y-%m-%d")
    if today in result:
        result["today"] = result[today]
    if tomorrow in result:
        result["tomorrow"] = result[tomorrow]

    return result


def fmt_day_night(dn: dict[str, Any] | None, key: str | None = None) -> str:
    """Format day/night info into a readable string.
    If key is None, pick the first available date.
    """
    if not dn:
        return ""
    if key is None:
        keys = sorted(dn.keys())
        if not keys:
            return ""
        key = keys[0]
    if key not in dn:
        return ""
    d = dn[key]
    parts = []
    if "day_low" in d and "day_high" in d:
        parts.append(f"☀️ Днём: {d['day_low']}..{d['day_high']}°C")
    elif "day_low" in d:
        parts.append(f"☀️ Днём: {d['day_low']}°C")
    if "night_low" in d and "night_high" in d:
        parts.append(f"🌙 Ночью: {d['night_low']}..{d['night_high']}°C")
    elif "night_low" in d:
        parts.append(f"🌙 Ночью: {d['night_low']}°C")
    return " | ".join(parts)


def fmt_precipitation(entries: list[dict[str, Any]]) -> str | None:
    """Return human-readable precipitation windows from raw forecast."""
    rain_blocks: list[dict[str, Any]] = []
    snow_blocks: list[dict[str, Any]] = []
    current_rain: dict[str, Any] | None = None
    current_snow: dict[str, Any] | None = None

    for e in entries:
        rain = e.get("rain", 0) or 0
        snow = e.get("snow", 0) or 0

        if rain > 0:
            if current_rain is None:
                current_rain = {"start": e["dt_txt"], "end": e["dt_txt"], "max": rain}
            else:
                current_rain["end"] = e["dt_txt"]
                current_rain["max"] = max(current_rain["max"], rain)
        else:
            if current_rain is not None:
                rain_blocks.append(current_rain)
                current_rain = None

        if snow > 0:
            if current_snow is None:
                current_snow = {"start": e["dt_txt"], "end": e["dt_txt"], "max": snow}
            else:
                current_snow["end"] = e["dt_txt"]
                current_snow["max"] = max(current_snow["max"], snow)
        else:
            if current_snow is not None:
                snow_blocks.append(current_snow)
                current_snow = None

    if current_rain is not None:
        rain_blocks.append(current_rain)
    if current_snow is not None:
        snow_blocks.append(current_snow)

    lines: list[str] = []

    for b in rain_blocks:
        start = _fmt_time(b["start"])
        end = _fmt_time(b["end"])
        lines.append(f"🌧 Дождь с {start} до {end}, до {b['max']:.1f} мм/3ч")

    for b in snow_blocks:
        start = _fmt_time(b["start"])
        end = _fmt_time(b["end"])
        lines.append(f"❄️ Снег с {start} до {end}, до {b['max']:.1f} мм/3ч")

    return "\n".join(lines) if lines else None


def _fmt_time(dt_str: str | None) -> str:
    if dt_str is None:
        return "—"
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%H:%M")
    except ValueError:
        return dt_str


def fmt_forecast(entries: list[dict[str, Any]], city: str | None = None) -> str:
    dn = fetch_day_night(city) if city else None
    lines = ["📅 <b>Прогноз на 7 дней</b>\n"]
    for e in entries:
        rain_info = ""
        if e.get("rain", 0) > 0:
            rain_info = f" 🌧{e['rain']}мм"
        if e.get("snow", 0) > 0:
            rain_info = f" ❄️{e['snow']}мм"
        date = e["date"]
        dn_line = fmt_day_night(dn, date)
        line = f"▫️ <b>{date}</b> — {e['temp']}°C, {e['desc']}{rain_info}\n   💧 {e['humidity']}% 💨 {e['wind']} м/с"
        if dn_line:
            line += f"\n   {dn_line}"
        lines.append(line)
    return "\n".join(lines)
