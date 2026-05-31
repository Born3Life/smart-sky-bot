from __future__ import annotations

import logging

import requests

from config import openrouter_api_key
from database import get_history
from models import WeatherData
from services.weather_forecast import fetch_day_night, fmt_day_night

logger = logging.getLogger(__name__)

BASE = "https://openrouter.ai/api/v1/chat/completions"


def _session() -> requests.Session:
    """Session that ignores HTTP_PROXY — proxy only for Telegram, not for AI."""
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

    kids_text = "есть маленькие дети" if has_children else "нет детей"

    dn = fetch_day_night(city or weather.city_name)
    dn_today = fmt_day_night(dn, "today")
    dn_tomorrow = fmt_day_night(dn, "tomorrow")

    from services.weather_forecast import fetch_raw_forecast
    from services.weather_forecast import fmt_precipitation
    raw = fetch_raw_forecast(city or weather.city_name)
    precip_warning = fmt_precipitation(raw) if raw else ""

    system_prompt = (
        "Ты — опытный метеоролог и персональный советник по погоде. "
        "Твои рекомендации конкретные, практичные и уникальные.\n\n"
        "Правила:\n"
        "1. Всегда учитывай профиль пользователя (дети, работа).\n"
        "2. Если есть дети — дай совет про одежду ребёнку, прогулку или дорогу в сад/школу.\n"
        "3. Если работа на улице — что надеть, взять с собой.\n"
        "4. Если работа в помещении — что надеть по пути, стоит ли брать зонт.\n"
        "5. Если сегодня дождь/снег/гроза — обязательно укажи время, "
        "когда ожидается, и дай конкретный совет.\n"
        "6. Пиши 3-5 предложений. Без воды. Каждое предложение — полезный факт.\n"
        "7. В конце обязательно обратись к пользователю по имени, пожелай хорошего дня.\n\n"
        "Формат:\n"
        "Конкретный совет исходя из погоды.\n"
        "Если нужен зонт/тёплая одежда/крем — напиши.\n"
        "Закончи: «{имя}, хорошего дня! ☀️»"
    )

    dn_info = ""
    if dn_today:
        dn_info += f"\nСегодня: {dn_today}"
    if dn_tomorrow:
        dn_info += f"\nЗавтра: {dn_tomorrow}"

    weather_text = (
        f"Город: {city or weather.city_name}. "
        f"Сейчас: {weather.temperature}°C, {weather.description}. "
        f"Ветер {weather.wind_speed} м/с, влажность {weather.humidity}%.{dn_info}"
    )
    if precip_warning:
        weather_text += f"\n\nОсадки сегодня:\n{precip_warning}"

    user_info = f"Пользователь: {kids_text}, работа: {workplace or 'не указана'}, имя: {user_name or 'не указано'}."

    messages = [{"role": "system", "content": system_prompt}]

    if user_id:
        history = get_history(user_id, limit=300)
        if history:
            context = "\n".join(f"{h['role']}: {h['text']}" for h in history[-10:])
            messages.append({
                "role": "system",
                "content": f"Недавний диалог пользователя:\n{context}",
            })

    messages.append({"role": "user", "content": f"{user_info}\n\n{weather_text}"})

    sess = _session()
    for model in ["openai/gpt-4o-mini", "openrouter/free"]:
        for attempt in range(2):
            try:
                resp = sess.post(
                    BASE,
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": 500,
                        "temperature": 0.8,
                    },
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
