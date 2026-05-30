from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import Command

from database import get_user_async
from keyboards.main import main_keyboard
from services.ai_recommendations import ai_tip
from services.recommendation import get_recommendations
from services.weather_forecast import fetch_forecast, fmt_forecast
from services.weather_text import fmt_weather
from weather import fetch_by_city

logger = logging.getLogger(__name__)

router = Router()


async def _get_city_profile(
    user_id: int,
) -> tuple[str | None, str | None, str | None]:
    info = await get_user_async(user_id)
    if not info:
        return None, None, None
    return (
        info.get("city"),
        info.get("profile_type", "Обычный"),
        info.get("is_premium", False),
    )


@router.message(F.text == "🌤 Погода")
@router.message(Command("weather"))
async def handle_weather(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, profile, _ = await _get_city_profile(user.id)
    if not city:
        await message.answer(
            "🏙 Сначала укажи город.\nНапиши название города (например: Москва).",
        )
        return
    if profile is None:
        await message.answer("Напиши /start, чтобы зарегистрироваться")
        return

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


@router.message(Command("forecast"))
async def handle_forecast(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, _, _ = await _get_city_profile(user.id)
    if not city:
        await message.answer("🏙 Сначала укажи город через /start или кнопку.")
        return

    sent = await message.answer("📅 Получаю прогноз...")
    forecast = fetch_forecast(city)
    if forecast is None:
        await sent.edit_text("❌ Не удалось получить прогноз.")
        return

    await sent.edit_text(fmt_forecast(forecast))


@router.message(Command("ai_tip"))
async def handle_ai_tip(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, profile, _ = await _get_city_profile(user.id)
    if not city or not profile:
        await message.answer("Сначала настрой профиль и город через /start.")
        return

    weather = fetch_by_city(city)
    if weather is None:
        await message.answer("❌ Не удалось получить погоду.")
        return

    sent = await message.answer("🤖 Генерирую AI-совет...")
    tip = ai_tip(profile, weather)
    if tip is None:
        await sent.edit_text(
            "❌ AI-совет временно недоступен.\n"
            "Попробуй позже или используй обычные рекомендации.",
        )
        return

    await sent.edit_text(f"🤖 <b>AI-рекомендация</b>\n\n{tip}")
