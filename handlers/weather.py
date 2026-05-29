from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import Command

from database import get_user_async
from keyboards.main import main_keyboard
from services.recommendation import get_recommendations
from services.weather_text import fmt_weather
from weather import fetch_by_city

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "🌤 Погода")
@router.message(Command("weather"))
async def handle_weather(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await get_user_async(user.id)
    if not info:
        await message.answer("Напиши /start, чтобы зарегистрироваться")
        return

    city = info.get("city")
    if not city:
        await message.answer(
            "🏙 Сначала укажи город.\nНапиши название города (например: Москва).",
        )
        return

    profile = info.get("profile_type", "Обычный")
    sent = await message.answer("🔍 Получаю данные о погоде...")

    weather = fetch_by_city(city)
    if weather is None:
        await sent.edit_text(
            f"❌ Не удалось получить погоду для «{city}».\n"
            "Проверь название города или попробуй позже.",
        )
        return

    weather_block = fmt_weather(weather)
    recommendations = get_recommendations(profile, weather)
    rec_lines = "\n".join(f"• {r}" for r in recommendations)

    full_text = (
        f"{weather_block}\n\n👤 <b>Рекомендации для «{profile}»:</b>\n{rec_lines}"
    )

    await sent.edit_text(full_text)
    await message.answer("Выбери действие:", reply_markup=main_keyboard())
