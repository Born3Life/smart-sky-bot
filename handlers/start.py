from __future__ import annotations

import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import get_user_async, upsert_user_async
from keyboards.main import main_keyboard, profile_keyboard
from models.states import Onboarding

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def handle_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user is None:
        return

    await upsert_user_async(user.id, user.username, user.full_name or "")

    info = await get_user_async(user.id)
    if info is None:
        info = {}

    name = info.get("full_name")
    profile = info.get("profile_type", "Обычный")
    city = info.get("city")

    # All fields present → welcome back
    if name and city:
        fallback = user.full_name or ""
        display_name = name or fallback
        await message.answer(
            f"С возвращением, {display_name}! 🌤\n\n"
            f"👤 Профиль: {profile}\n"
            f"🏙 Город: {city}\n\n"
            "Нажми «🌤 Сейчас», чтобы узнать погоду!",
            reply_markup=main_keyboard(),
        )
        return

    # Start onboarding from first missing field
    await state.set_state(Onboarding.waiting_name)
    await message.answer(
        "👋 <b>Привет! Я SmartSkyBot</b> — твой погодный помощник 🌤\n\n"
        "Давай заполним твой профиль по порядку.\n\n"
        "<b>Как тебя зовут?</b>",
    )
