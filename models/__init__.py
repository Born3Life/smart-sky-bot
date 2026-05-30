from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class UserDict(TypedDict, total=False):
    user_id: int
    username: str | None
    full_name: str | None
    profile_type: str
    city: str | None
    city_lat: float | None
    city_lon: float | None
    registered_at: str
    is_active: bool
    is_premium: bool
    premium_until: str | None
    referred_by: int | None
    referral_code: str | None
    notifications_enabled: bool
    notify_time: str
    language: str
    workplace: str
    has_children: int


@dataclass
class WeatherData:
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float
    wind_gust: float | None
    pressure: int
    description: str
    icon: str
    rain_1h: float | None
    snow_1h: float | None
    clouds: int
    visibility: int
    city_name: str
    country: str
    sunrise: int | None = None
    sunset: int | None = None
    uvi: float | None = None


PROFILE_BUTTONS: dict[str, str] = {
    "👷 Строитель": "Строитель",
    "🚗 Водитель": "Водитель",
    "👨‍👩‍👧‍👦 Родитель": "Родитель",
    "🌱 Дачник": "Дачник",
    "🎣 Рыбак": "Рыбак",
    "👤 Обычный": "Обычный",
    "🏃 Спортсмен": "Спортсмен",
    "🤧 Аллергик": "Аллергик",
}

PROFILES: list[str] = list(PROFILE_BUTTONS.values())
