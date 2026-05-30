from __future__ import annotations

import logging

import requests

from config import openrouter_api_key
from models import WeatherData

logger = logging.getLogger(__name__)

BASE = "https://openrouter.ai/api/v1/chat/completions"

AI_PROMPT = (
    "Ты — метеоролог. Дай краткие персонализированные рекомендации "
    "на основе данных погоды. Учти профиль пользователя: {profile}. "
    "Напиши 2-3 совета на русском. Без лишних слов."
)


def ai_tip(profile: str, weather: WeatherData) -> str | None:
    api_key = openrouter_api_key()
    if not api_key:
        return None

    prompt = AI_PROMPT.format(profile=profile)
    weather_text = (
        f"Температура: {weather.temperature}°C, "
        f"ветер: {weather.wind_speed} м/с, "
        f"влажность: {weather.humidity}%, "
        f"давление: {weather.pressure} гПа, "
        f"осадки: {weather.rain_1h or 0} мм, "
        f"описание: {weather.description}"
    )

    try:
        resp = requests.post(
            BASE,
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": weather_text},
                ],
                "max_tokens": 200,
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("AI recommendation failed")
        return None
