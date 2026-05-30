from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import StateFilter

from database import update_city_async
from keyboards.main import main_keyboard
from weather import fetch_by_city

logger = logging.getLogger(__name__)

router = Router()

# All button texts from main_keyboard that should NOT be treated as city names
_BUTTONS = {
    "🌤 Сейчас",
    "📅 Сегодня",
    "📅 Завтра",
    "📅 7 дней",
    "🌅 Рассвет",
    "☀️ UV-индекс",
    "🤖 AI Совет",
    "📍 Погода здесь",
    "👤 Профиль",
    "🏙 Город",
    "💎 Премиум",
    "🔙 Назад",
    "/start",
    "/subscribe",
    "/subscribe@smart_sky_bot",
}


@router.message(F.text == "🏙 Город", StateFilter(None))
async def handle_change_city_prompt(message: types.Message) -> None:
    await message.answer(
        "🏙 Напиши название города (например: Москва, Лондон):",
    )


@router.message(StateFilter(None))
async def handle_city_or_weather(message: types.Message) -> None:
    user = message.from_user
    if user is None or not message.text:
        return

    text = message.text.strip()

    if text in _BUTTONS:
        return

    weather = fetch_by_city(text)
    if weather is not None:
        await update_city_async(user.id, text)
        await message.answer(
            f"✅ Город <b>{text}</b> сохранён!\nНажми «🌤 Сейчас» для прогноза.",
            reply_markup=main_keyboard(),
        )
    else:
        await message.answer(
            f"❌ Город «{text}» не найден.\nПроверь название и попробуй ещё раз.",
        )
