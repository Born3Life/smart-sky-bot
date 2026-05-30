from __future__ import annotations

import logging

import requests

from config import openrouter_api_key
from database import get_history
from models import WeatherData

logger = logging.getLogger(__name__)

BASE = "https://openrouter.ai/api/v1/chat/completions"


def ai_tip(
    has_children: int,
    workplace: str,
    weather: WeatherData,
    city: str | None = None,
    user_id: int | None = None,
) -> str | None:
    api_key = openrouter_api_key()
    if not api_key:
        return None

    kids = "есть маленькие дети" if has_children else "нет детей"
    prompt = (
        "Ты — метеоролог. Дай одну персонализированную рекомендацию.\n"
        f"Пользователь: {kids}, работа: {workplace or 'не указана'}.\n"
        "Если есть дети — дай совет про них. "
        "Если работа на улице — что взять с собой. "
        "Если работа в помещении — что надеть.\n"
        "Один совет, 1-2 предложения, по-русски. Без лишних слов."
    )

    weather_text = (
        f"Город: {city or weather.city_name}. "
        f"Сейчас: {weather.temperature}°C, {weather.description}. "
        f"Ветер {weather.wind_speed} м/с, влажность {weather.humidity}%."
    )

    messages = [{"role": "system", "content": prompt}]

    if user_id:
        history = get_history(user_id, limit=300)
        for h in history:
            messages.append({"role": h["role"], "content": h["text"]})

    messages.append({"role": "user", "content": weather_text})

    try:
        resp = requests.post(
            BASE,
            json={
                "model": "openai/gpt-4o-mini",
                "messages": messages,
                "max_tokens": 150,
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("AI recommendation failed")
        return None
