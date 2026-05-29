from __future__ import annotations

from models import WeatherData


def _builder(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if w.rain_1h and w.rain_1h > 0:
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
    if w.rain_1h and w.rain_1h > 2:
        tips.append("🌧 Сильный дождь — увеличь дистанцию")
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
    if w.rain_1h and w.rain_1h > 0:
        tips.append("☔ Не забудь зонт и непромокаемую обувь")
    if not tips:
        tips.append("✅ Погода комфортная для прогулки с ребёнком")
    return tips


def _gardener(w: WeatherData) -> list[str]:
    tips: list[str] = []
    if w.temperature < 0:
        tips.append("❄️ Заморозки — укрой растения на ночь")
    if w.rain_1h and w.rain_1h > 0:
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
    if w.rain_1h and w.rain_1h > 0:
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
    if w.rain_1h and w.rain_1h > 2:
        tips.append("🌧 Сильный дождь — оставайся дома, если можно")
    if w.wind_speed > 12:
        tips.append("💨 Ветрено — убери с балкона лёгкие вещи")
    if not tips:
        tips.append("✅ Погода комфортная — наслаждайся днём!")
    return tips


_RECOMMENDATIONS = {
    "Строитель": _builder,
    "Водитель": _driver,
    "Родитель": _parent,
    "Дачник": _gardener,
    "Рыбак": _fisher,
    "Обычный": _default,
}


def get_recommendations(profile: str, weather: WeatherData) -> list[str]:
    func = _RECOMMENDATIONS.get(profile, _default)
    return func(weather)
