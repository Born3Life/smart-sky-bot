from __future__ import annotations

from models import WeatherData

from .weather_forecast import fetch_raw_forecast, fmt_precipitation


def _has_rain(w: WeatherData) -> bool:
    desc = w.description.lower()
    return bool(
        (w.rain_1h and w.rain_1h > 0)
        or any(k in desc for k in ("дожд", "гроз", "ливн", "осадк")),
    )


def _builder(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if _has_rain(w):
        tips.append("🌧 Возьми дождевик — ожидаются осадки")
    if w.temperature < 0:
        tips.append("❄️ Возможны заморозки — проверь смеси и растворы")
    if w.wind_speed > 10:
        tips.append("💨 Сильный ветер — отложи высотные работы")
    if w.temperature > 30:
        tips.append("☀️ Жара — пей воду и работай в тени")
    if not tips:
        tips.append("✅ Погода рабочая — можно строить!")
    return tips


def _driver(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if w.temperature < 0 and w.humidity > 80:
        tips.append("⚠️ Гололедица — будь аккуратен на дороге")
    if w.visibility and w.visibility < 1000:
        tips.append("🌫 Туман — включи противотуманки, снизь скорость")
    if w.wind_speed > 12:
        tips.append("💨 Сильный ветер — осторожно на мостах и трассах")
    if _has_rain(w):
        tips.append("🌧 Дождь — увеличь дистанцию, включи дворники")
    if w.snow_1h and w.snow_1h > 0:
        tips.append("❄️ Снегопад — проверь резину")
    if not tips:
        tips.append("✅ Дорожные условия благоприятные")
    return tips


def _parent(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if w.temperature < -5:
        tips.append("🧥 Ребёнку нужен тёплый комбинезон, шапка и шарф")
    elif w.temperature < 5:
        tips.append("🧥 Одень ребёнка в куртку потеплее")
    elif w.temperature > 25:
        tips.append("👕 Лёгкая одежда, головной убор и вода обязательны")
    if w.wind_speed > 8:
        tips.append("💨 Ветрено — закрой уши и горло ребёнку")
    if _has_rain(w):
        tips.append("☔ Не забудь зонт и непромокаемую обувь")
    if not tips:
        tips.append("✅ Погода комфортная для прогулки с ребёнком")
    return tips


def _gardener(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if w.temperature < 0:
        tips.append("❄️ Заморозки — укрой растения на ночь")
    if _has_rain(w):
        tips.append("💧 Полив не нужен — дождь сделает работу")
    elif w.temperature > 20 and w.humidity < 50:
        tips.append("💦 Засушливо — пора поливать грядки")
    if w.wind_speed > 8:
        tips.append("🌬 Сильный ветер — проверь подвязки растений")
    if not tips:
        tips.append("✅ Хороший день для работы в саду")
    return tips


def _fisher(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if w.wind_speed > 8:
        tips.append("🎣 Ветер сильный — клёв слабый, ищи затишье")
    elif w.wind_speed < 3:
        tips.append("🎣 Штиль — отличный клёв!")
    pressure_mm = w.pressure * 0.750064
    if pressure_mm < 745:
        tips.append("📉 Давление низкое — рыба активна, но капризна")
    elif pressure_mm > 765:
        tips.append("📈 Давление высокое — попробуй донку")
    if _has_rain(w):
        tips.append("🌧 Дождь — рыба уходит на глубину")
    if not tips:
        tips.append("✅ Хорошие условия для рыбалки!")
    return tips


def _default(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if w.temperature > 30:
        tips.append("☀️ Жарко — избегай долгого пребывания на солнце")
    elif w.temperature < -10:
        tips.append("🥶 Очень холодно — одевайся многослойно")
    if _has_rain(w):
        tips.append("🌧 Дождь — возьми зонт, одевайся по погоде")
    if w.wind_speed > 12:
        tips.append("💨 Ветрено — убери с балкона лёгкие вещи")
    if not tips:
        tips.append("✅ Погода комфортная — наслаждайся днём!")
    return tips


def _sports(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if w.temperature > 28:
        tips.append("🥵 Жара — перенеси тренировку на утро/вечер")
    elif w.temperature < -10:
        tips.append("🥶 Мороз — короткая тренировка, тёплая одежда")
    if w.wind_speed > 8:
        tips.append("💨 Сильный ветер — вело/бег будут тяжёлыми")
    if _has_rain(w):
        tips.append("🌧 Дождь — скользко, выбери крытый зал")
    if w.humidity > 85:
        tips.append("💧 Высокая влажность — тяжело дышать, снизь темп")
    if not tips:
        tips.append("✅ Отличная погода для тренировки!")
    return tips


def _allergy(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if w.temperature > 20 and w.humidity > 60:
        tips.append("🌿 Высокий риск пыльцы — закрой окна, прими антигистамин")
    if w.wind_speed > 5:
        tips.append("💨 Ветер разносит пыльцу — надень маску на улице")
    if _has_rain(w):
        tips.append("🌧 Дождь прибивает пыльцу — хороший день для прогулки")
    if w.humidity > 80:
        tips.append("💧 Сырость — риск плесени, проветривай")
    if not tips:
        tips.append("✅ Низкий риск аллергии")
    return tips


_RECOMMENDATIONS = {
    "Строитель": _builder,
    "Водитель": _driver,
    "Родитель": _parent,
    "Дачник": _gardener,
    "Рыбак": _fisher,
    "Обычный": _default,
    "Спортсмен": _sports,
    "Аллергик": _allergy,
}


def get_recommendations(
    profile: str,
    weather: WeatherData,
    city: str | None = None,
) -> list[str]:
    func = _RECOMMENDATIONS.get(profile, _default)
    tips = func(weather)

    if city:
        forecast = fetch_raw_forecast(city)
        if forecast:
            precip = fmt_precipitation(forecast)
            if precip:
                tips.insert(0, precip)

    return tips
