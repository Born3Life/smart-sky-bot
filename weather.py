from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from config import openweather_api_key
from models import WeatherData

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
UV_URL = "https://api.openweathermap.org/data/2.5/uvi"


def _parse(data: dict[str, Any], city_name: str) -> WeatherData:
    main = data["main"]
    wind = data["wind"]
    weather = data["weather"][0]
    rain = (data.get("rain") or {}).get("1h")
    snow = (data.get("snow") or {}).get("1h")
    sys = data.get("sys", {})

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
        country=sys.get("country", ""),
        sunrise=sys.get("sunrise"),
        sunset=sys.get("sunset"),
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
        weather = _parse(data, data.get("name", city))
        weather.uvi = _fetch_uvi(data["coord"]["lat"], data["coord"]["lon"])
        return weather
    except requests.RequestException:
        logger.exception("OpenWeather API error for city=%s", city)
        return None


def fetch_by_coords(lat: float, lon: float) -> WeatherData | None:
    api_key = openweather_api_key()
    if not api_key:
        return None

    try:
        resp = requests.get(
            BASE_URL,
            params={
                "lat": lat,
                "lon": lon,
                "appid": api_key,
                "units": "metric",
                "lang": "ru",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        weather = _parse(data, data.get("name", f"{lat},{lon}"))
        weather.uvi = _fetch_uvi(lat, lon)
        return weather
    except requests.RequestException:
        logger.exception("OpenWeather API error for coords")
        return None


def _fetch_uvi(lat: float, lon: float) -> float | None:
    api_key = openweather_api_key()
    if not api_key:
        return None
    try:
        resp = requests.get(
            UV_URL,
            params={"lat": lat, "lon": lon, "appid": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("value")
    except requests.RequestException:
        return None


def ts_to_time(ts: int | None) -> str:
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%H:%M")
