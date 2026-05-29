from __future__ import annotations

import logging
from typing import Any

import requests

from config import openweather_api_key
from models import WeatherData

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def _parse(data: dict[str, Any], city_name: str) -> WeatherData:
    main = data["main"]
    wind = data["wind"]
    weather = data["weather"][0]
    rain = (data.get("rain") or {}).get("1h")
    snow = (data.get("snow") or {}).get("1h")

    return WeatherData(
        temperature=main["temp"],
        feels_like=main["feels_like"],
        humidity=main["humidity"],
        wind_speed=wind["speed"],
        wind_gust=wind.get("gust"),
        pressure=main["pressure"],
        description=weather["description"],
        icon=weather["icon"],
        rain_1h=rain,
        snow_1h=snow,
        clouds=data.get("clouds", {}).get("clouds", 0),
        visibility=data.get("visibility", 10000),
        city_name=city_name,
        country=data.get("sys", {}).get("country", ""),
    )


def fetch_by_city(city: str) -> WeatherData | None:
    api_key = openweather_api_key()
    if not api_key:
        logger.warning("OPENWEATHER_API_KEY not set")
        return None

    try:
        resp = requests.get(
            BASE_URL,
            params={"q": city, "appid": api_key, "units": "metric", "lang": "ru"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return _parse(data, data.get("name", city))
    except requests.RequestException:
        logger.exception("OpenWeather API error for city=%s", city)
        return None
