from __future__ import annotations

import logging

from aiogram import F, Router, types

from database import update_city_async
from keyboards.main import main_keyboard
from weather import fetch_by_city

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "🏙 Изменить город")
async def handle_change_city_prompt(message: types.Message) -> None:
    await message.answer(
        "🏙 Напиши название города (например: Москва, Лондон):",
    )


@router.message()
async def handle_city_or_weather(message: types.Message) -> None:
    user = message.from_user
    if user is None or not message.text:
        return

    text = message.text.strip()

    # Skip menu buttons
    if text in ("🌤 Погода", "👤 Профиль", "🏙 Изменить город", "/start"):
        return

    # Try as city name
    weather = fetch_by_city(text)
    if weather is not None:
        await update_city_async(user.id, text)
        await message.answer(
            f"✅ Город <b>{text}</b> сохранён!\nНажми «🌤 Погода» для прогноза.",
            reply_markup=main_keyboard(),
        )
    else:
        await message.answer(
            f"❌ Город «{text}» не найден.\nПроверь название и попробуй ещё раз.",
        )
