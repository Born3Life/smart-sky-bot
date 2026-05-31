from __future__ import annotations

import logging
from datetime import datetime

import requests

from config import openrouter_api_key
from database import get_history
from models import WeatherData
from services.weather_forecast import fetch_day_night, fmt_day_night

logger = logging.getLogger(__name__)

BASE = "https://openrouter.ai/api/v1/chat/completions"


def _session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.verify = False
    return s


def ai_tip(
    has_children: int,
    workplace: str,
    weather: WeatherData,
    city: str | None = None,
    user_id: int | None = None,
    user_name: str = "",
) -> str | None:
    api_key = openrouter_api_key()
    if not api_key:
        return None

    dn = fetch_day_night(city or weather.city_name)
    dn_today = fmt_day_night(dn, "today")
    dn_tomorrow = fmt_day_night(dn, "tomorrow")

    from services.weather_forecast import fetch_raw_forecast, fmt_precipitation
    raw = fetch_raw_forecast(city or weather.city_name)
    precip_warning = fmt_precipitation(raw) if raw else ""

    now = datetime.utcnow()
    hour = now.hour
    time_of_day = "утро" if 5 <= hour < 12 else "день" if 12 <= hour < 18 else "вечер" if 18 <= hour < 23 else "ночь"

    system_prompt = (
        "Ты — живой, умный собеседник и эксперт по погоде. "
        "Твоя задача — не просто выдать факты, а подумать, проанализировать и дать "
        "человечный, полезный совет.\n\n"
        "Как ты думаешь:\n"
        "1. Посмотри на погоду: температура, осадки, ветер, влажность, давление.\n"
        "2. Посмотри на пользователя: есть ли дети, где работает, как зовут.\n"
        "3. Посмотри на историю диалога: о чём уже говорили.\n"
        "4. Сделай вывод: что важно именно сейчас для этого человека.\n"
        "5. Дай совет — конкретный, тёплый, человечный.\n\n"
        "Правила:\n"
        "- Если дети — подумай про их одежду, прогулку, садик/школу.\n"
        "- Если работа на улице — что надеть, взять с собой.\n"
        "- Если работа в офисе — как одеться по пути, нужен ли зонт.\n"
        "- Если дождь/снег/гроза — предупреди, укажи время, посоветуй что делать.\n"
        "- Пиши как живой человек: 3-5 предложений, тепло, по делу.\n"
        "- Обращайся к человеку по имени естественно, вплетай в текст, "
        "не обязательно в конце. Разные фразы (не шаблон).\n"
        "- Не будь роботом. Будь другом, который заботится."
    )

    dn_info = ""
    if dn_today:
        dn_info += f"\n- Днём: {dn_today}"
    if dn_tomorrow:
        dn_info += f"\n- Завтра: {dn_tomorrow}"

    weather_report = (
        f"📍 Город: {city or weather.city_name}\n"
        f"🕐 {time_of_day}\n"
        f"🌡 Сейчас: {weather.temperature}°C, ощущается как {weather.feels_like}°C\n"
        f"☁️ {weather.description}\n"
        f"💨 Ветер: {weather.wind_speed} м/с"
    )
    if weather.wind_gust is not None:
        weather_report += f", порывы до {weather.wind_gust} м/с"
    weather_report += (
        f"\n💧 Влажность: {weather.humidity}%\n"
        f"📊 Давление: {weather.pressure} гПа"
    )
    if weather.uvi is not None:
        weather_report += f"\n☀️ UV-индекс: {weather.uvi}"
    if dn_info:
        weather_report += dn_info
    if precip_warning:
        weather_report += f"\n\n⚠️ Осадки сегодня:\n{precip_warning}"

    kids_info = "👶 есть маленькие дети" if has_children else "👤 без детей"
    work_info = f"💼 работа: {workplace}" if workplace else "💼 работа не указана"
    user_profile = f"{kids_info}, {work_info}, имя: {user_name or '—'}."

    messages = [{"role": "system", "content": system_prompt}]

    if user_id:
        history = get_history(user_id, limit=300)
        if history:
            recent = history[-6:]
            formatted = "\n".join(
                f"{'Пользователь' if h['role'] == 'user' else 'Бот'}: {h['text']}"
                for h in recent
            )
            messages.append({
                "role": "system",
                "content": f"Недавний разговор с пользователем:\n{formatted}",
            })

    messages.append({
        "role": "user",
        "content": (
            f"Профиль: {user_profile}\n\n"
            f"Погода:\n{weather_report}\n\n"
            "Посмотри на всё это и дай человеку тёплый, умный совет "
            "на день. Что важно учесть? Что посоветуешь?"
        ),
    })

    sess = _session()
    for model in ["openai/gpt-4o-mini", "openrouter/free"]:
        for attempt in range(2):
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": 600,
                    "temperature": 0.9,
                    "top_p": 0.95,
                }
                resp = sess.post(
                    BASE,
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30,
                )
                data = resp.json()
                if "error" not in data:
                    return data["choices"][0]["message"]["content"]
                err = data.get("error", {})
                logger.warning("AI model %s error: %s", model, err.get("message") or err)
            except Exception as e:
                logger.warning("AI request failed on %s: %s", model, e)

    return None
