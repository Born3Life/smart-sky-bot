from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from models import WeatherData

logger = logging.getLogger(__name__)

_BASE = "https://www.gismeteo.ru"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# city_russian_name -> (english_slug, gismeteo_id)
_CITIES: dict[str, tuple[str, int]] = {
    "москва": ("moscow", 4368),
    "санкт-петербург": ("saint-petersburg", 4079),
    "петербург": ("saint-petersburg", 4079),
    "новосибирск": ("novosibirsk", 4690),
    "екатеринбург": ("yekaterinburg", 4516),
    "казань": ("kazan", 4446),
    "нижний новгород": ("nizhny-novgorod", 4530),
    "челябинск": ("chelyabinsk", 4592),
    "самара": ("samara", 4618),
    "омск": ("omsk", 4650),
    "ростов-на-дону": ("rostov-na-donu", 4627),
    "уфа": ("ufa", 4563),
    "красноярск": ("krasnoyarsk", 4674),
    "воронеж": ("voronezh", 4490),
    "пермь": ("perm", 4568),
    "волгоград": ("volgograd", 4588),
    "северск": ("seversk", 12839),
    "томск": ("tomsk", 4663),
    "тюмень": ("tyumen", 4583),
    "сочи": ("sochi", 4247),
    "лондон": ("london", 5095),
    "париж": ("paris", 5083),
    "берлин": ("berlin", 5097),
    "нью-йорк": ("new-york", 5091),
}

_ICON_MAP: dict[str, str] = {
    "c": "01d", "cl": "02d", "c_": "03d", "d": "04d",
    "d_c1": "09d", "d_c2": "10d", "d_c3": "10d",
    "d_c4": "11d", "s": "13d", "s_c1": "13d", "f": "50d",
}

_DESC_MAP: dict[str, str] = {
    "c": "ясно", "cl": "облачно", "c_": "облачно",
    "d": "пасмурно", "d_c1": "дождь", "d_c2": "дождь",
    "d_c3": "дождь", "d_c4": "гроза",
    "s": "снег", "s_c1": "снег", "f": "туман",
}


def _gismeteo_icon(icon: str) -> str:
    return _ICON_MAP.get(icon, "01d")


def _description(icon: str) -> str:
    return _DESC_MAP.get(icon, "ясно")


def _extract_json_block(text: str, key: str) -> dict[str, Any] | None:
    """Extract a named JSON block from the page config."""
    idx = text.find(f'"{key}"')
    if idx < 0:
        return None
    start = text.rfind("{", idx - 500, idx)
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        if depth == 0 and i > start:
            try:
                return json.loads(text[start : i + 1])
            except json.JSONDecodeError:
                return None
    return None


def _city_url(city: str) -> str | None:
    entry = _CITIES.get(city.lower().strip())
    if entry:
        slug, cid = entry
        return f"{_BASE}/weather-{slug}-{cid}/now/"
    return None


def fetch_by_city(city: str) -> WeatherData | None:
    url = _city_url(city)
    if url is None:
        return None

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        logger.warning("gismeteo fetch failed for %s", city)
        return None

    text = resp.text

    # Extract current weather from JSON
    data = _extract_json_block(text, "cw")
    if data is None:
        logger.warning("no cw block in gismeteo page for %s", city)
        return None

    cw = data.get("cw", data)
    if not isinstance(cw, dict):
        return None

    def _val(key: str) -> Any:
        raw = cw.get(key)
        if isinstance(raw, list) and len(raw) > 0:
            return raw[0]
        return raw

    temp = _val("temperatureAir")
    if temp is None:
        return None

    feels = _val("temperatureFeelsLike") or temp
    humidity = _val("humidity") or 0
    wind = _val("windSpeed") or 0
    gust = _val("windGust")
    precip = _val("precipitation") or 0
    press_mmhg = _val("pressure") or 0
    icon_raw = str(_val("iconWeather") or "c")

    press_hpa = round(press_mmhg * 1.333) if press_mmhg else 0
    desc = _description(icon_raw)

    # City name from breadcrumb
    city_display = city
    for key, (slug, _cid) in _CITIES.items():
        if slug in url:
            city_display = key.capitalize()
            break

    return WeatherData(
        temperature=float(temp),
        feels_like=float(feels),
        humidity=int(humidity),
        wind_speed=float(wind),
        wind_gust=float(gust) if gust is not None else None,
        pressure=press_hpa,
        description=desc,
        icon=_gismeteo_icon(icon_raw),
        rain_1h=float(precip) if float(precip) > 0 else None,
        snow_1h=None,
        clouds=0,
        visibility=10000,
        city_name=city_display,
        country="",
    )


def fetch_today_hourly(city: str) -> list[dict[str, Any]] | None:
    """Fetch today's hourly forecast from gismeteo."""
    url = _city_url(city)
    if url is None:
        return None

    try:
        main_url = url.replace("/now/", "/")
        resp = requests.get(main_url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    text = resp.text

    data = _extract_json_block(text, "cw")
    if data is None:
        return None

    cw = data.get("cw", data)
    if not isinstance(cw, dict):
        return None

    # The cw block seems to have only current weather, not hourly
    # We need to find the forecast data
    # Try extracting from known patterns in the page
    entries: list[dict[str, Any]] = []

    # Parse the temperature row from the page
    temp_match = re.search(
        r'"temperatureAir"\s*:\s*\[([^\]]+)\]',
        text,
    )
    if temp_match:
        # Extract date/icon pairs
        dates = re.findall(r'"date"\s*:\s*\["([^"]+)"\]', text)
        icons = re.findall(r'"iconWeather"\s*:\s*\["([^"]+)"\]', text)

        for i in range(min(len(dates), len(icons))):
            entries.append({
                "date": dates[i],
                "icon": icons[i],
                "desc": _description(icons[i]),
            })

    if not entries:
        # Fallback: current weather as single entry
        icon_raw = str(
            cw.get("iconWeather", ["c"])[0]
            if isinstance(cw.get("iconWeather"), list)
            else cw.get("iconWeather", "c")
        )
        entries.append({
            "date": cw.get("date", [""])[0] if isinstance(cw.get("date"), list) else "",
            "icon": icon_raw,
            "desc": _description(icon_raw),
        })

    return entries if entries else None
