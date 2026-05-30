from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from models import WeatherData

logger = logging.getLogger(__name__)

BASE = "https://www.gismeteo.ru"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

_CITY_IDS: dict[str, tuple[str, int]] = {
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
    "иркутск": ("irkutsk", 4668),
    "владивосток": ("vladivostok", 4716),
    "хабаровск": ("khabarovsk", 4728),
    "сочи": ("sochi", 4247),
    "лондон": ("london", 5095),
    "париж": ("paris", 5083),
    "берлин": ("berlin", 5097),
    "нью-йорк": ("new-york", 5091),
    "пекин": ("beijing", 5070),
    "токио": ("tokyo", 5099),
    "дубай": ("dubai", 5093),
    "прага": ("prague", 5064),
}


def _slugify(text: str) -> str:
    mapping = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
        " ": "-",
    }
    return "".join(mapping.get(ch, ch) for ch in text.lower().strip())


def _city_url(city: str) -> str | None:
    city_lower = city.lower().strip()
    entry = _CITY_IDS.get(city_lower)
    if entry is not None:
        slug, city_id = entry
        return f"{BASE}/weather-{slug}-{city_id}/now/"
    slug = _slugify(city_lower)
    if slug:
        return f"{BASE}/weather-{slug}-0/"
    return None


_ICON_MAP: dict[str, str] = {
    "c": "01d",
    "cl": "02d",
    "c_": "03d",
    "d": "04d",
    "d_c1": "09d",
    "d_c2": "10d",
    "d_c3": "10d",
    "d_c4": "11d",
    "s": "13d",
    "s_c1": "13d",
    "f": "50d",
}


def _owm_icon(gismeteo_icon: str) -> str:
    prefix = gismeteo_icon.split("_")[0] if "_" in gismeteo_icon else gismeteo_icon
    return _ICON_MAP.get(gismeteo_icon, _ICON_MAP.get(prefix, "01d"))


_DESC_MAP: dict[str, str] = {
    "c": "ясно",
    "cl": "облачно",
    "c_": "облачно",
    "d": "пасмурно",
    "d_c1": "дождь",
    "d_c2": "дождь",
    "d_c3": "дождь",
    "d_c4": "гроза",
    "s": "снег",
    "s_c1": "снег",
    "f": "туман",
}


def _description(icon: str) -> str:
    return _DESC_MAP.get(icon, "ясно")


def fetch_by_city(city: str) -> WeatherData | None:
    url = _city_url(city)
    if url is None:
        return None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("gismeteo fetch failed for %s", city)
        return None

    text = resp.text

    # Extract embedded JSON data
    json_match = re.search(r'\[\s*\{[^}]+"temperatureAir"[^}]+\}\s*\]', text)
    if not json_match:
        json_match = re.search(r'"temperatureAir"\s*:\s*\[(\d+)\]', text)
        if not json_match:
            logger.warning("no weather data found in gismeteo page for %s", city)
            return None

        # Parse scalar values from embedded JSON
        def _val(key: str) -> Any:
            m = re.search(rf'"{key}"\s*:\s*\[([^\]]+)\]', text)
            if m:
                raw = m.group(1)
                try:
                    return json.loads(f"[{raw}]")[0]
                except (json.JSONDecodeError, IndexError):
                    return None
            return None

        temp = _val("temperatureAir")
        feels = _val("temperatureFeelsLike")
        humidity = _val("humidity")
        pressure = _val("pressure")
        precip = _val("precipitation")
        wind = _val("windSpeed")
        gust = _val("windGust")
        icon_raw = _val("iconWeather")

        if temp is None:
            logger.warning("no temperature in gismeteo data for %s", city)
            return None

        icon_str = str(icon_raw) if icon_raw else "c"
        desc = _description(icon_str)

        # Pressure from gismeteo is in mmHg
        press_hpa = round(pressure * 1.333) if pressure else 0

        # City name from page title
        city_display = city
        title_match = re.search(
            r"Погода в\s+([^<>\n]+?)\s*(?:на\s+сегодня|сегодня)",
            text,
        )
        if title_match:
            city_display = title_match.group(1).strip()

        return WeatherData(
            temperature=float(temp),
            feels_like=float(feels) if feels is not None else float(temp),
            humidity=int(humidity) if humidity is not None else 0,
            wind_speed=float(wind) if wind is not None else 0.0,
            wind_gust=float(gust) if gust is not None else None,
            pressure=press_hpa,
            description=desc,
            icon=_owm_icon(icon_str),
            rain_1h=float(precip) if precip and float(precip) > 0 else None,
            snow_1h=None,
            clouds=0,
            visibility=10000,
            city_name=city_display,
            country="",
        )

    # Parse full JSON array
    try:
        data_list = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        logger.warning("failed to parse gismeteo JSON for %s", city)
        return None

    if not data_list:
        return None

    entry = data_list[0]
    temp = entry.get("temperatureAir")
    if temp is None:
        return None

    icon_str = entry.get("iconWeather", "c") or "c"
    desc = _description(icon_str)
    press_mmhg = entry.get("pressure", 0) or 0
    press_hpa = round(press_mmhg * 1.333) if press_mmhg else 0

    city_display = city
    title_match = re.search(r"Погода в\s+([^<>\n]+?)\s*(?:на\s+сегодня|сегодня)", text)
    if title_match:
        city_display = title_match.group(1).strip()

    return WeatherData(
        temperature=float(temp),
        feels_like=float(entry.get("temperatureFeelsLike", temp)),
        humidity=int(entry.get("humidity", 0)),
        wind_speed=float(entry.get("windSpeed", 0)),
        wind_gust=float(entry.get("windGust")) if entry.get("windGust") else None,
        pressure=press_hpa,
        description=desc,
        icon=_owm_icon(icon_str),
        rain_1h=(
            float(entry.get("precipitation", 0))
            if (entry.get("precipitation") or 0) > 0
            else None
        ),
        snow_1h=None,
        clouds=0,
        visibility=10000,
        city_name=city_display,
        country="",
    )
