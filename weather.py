from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from config import openweather_api_key
from models import WeatherData
from services.gismeteo import fetch_by_city as gismeteo_fetch

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
UV_URL = "https://api.openweathermap.org/data/2.5/uvi"


GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"


def _ow_geocode(city: str) -> tuple[float, float] | None:
    api_key = openweather_api_key()
    if not api_key:
        return None
    try:
        resp = requests.get(
            GEO_URL,
            params={"q": city, "limit": 1, "appid": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            return data[0]["lat"], data[0]["lon"]
    except requests.RequestException:
        pass
    return None


def fetch_by_city(city: str) -> WeatherData | None:
    """Try gismeteo first, fall back to OpenWeather."""
    weather = gismeteo_fetch(city)
    if weather is not None:
        logger.info("gismeteo OK for %s", city)
        if weather.uvi is None:
            coords = _ow_geocode(city)
            if coords:
                uv = _ow_fetch_uvi(*coords)
                weather.uvi = uv
        return weather

    logger.info("gismeteo failed, fallback to OpenWeather for %s", city)
    return _ow_fetch_by_city(city)


def fetch_by_coords(lat: float, lon: float) -> WeatherData | None:
    """Fallback: OpenWeather by coords."""
    return _ow_fetch_by_coords(lat, lon)


def ts_to_time(ts: int | None) -> str:
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%H:%M")


# ---------- OpenWeather fallbacks ----------


def _ow_parse(data: dict[str, Any], city_name: str) -> WeatherData:
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


def _ow_fetch_by_city(city: str) -> WeatherData | None:
    api_key = openweather_api_key()
    if not api_key:
        return None

    try:
        resp = requests.get(
            BASE_URL,
            params={"q": city, "appid": api_key, "units": "metric", "lang": "ru"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        weather = _ow_parse(data, data.get("name", city))
        try:
            weather.uvi = _ow_fetch_uvi(
                data["coord"]["lat"],
                data["coord"]["lon"],
            )
        except Exception:
            pass
        return weather
    except requests.RequestException:
        logger.exception("OpenWeather API error for city=%s", city)
        return None


def _ow_fetch_by_coords(lat: float, lon: float) -> WeatherData | None:
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
        weather = _ow_parse(data, data.get("name", f"{lat},{lon}"))
        weather.uvi = _ow_fetch_uvi(lat, lon)
        return weather
    except requests.RequestException:
        logger.exception("OpenWeather API error for coords")
        return None


def _ow_fetch_uvi(lat: float, lon: float) -> float | None:
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
