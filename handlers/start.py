from __future__ import annotations

import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.markdown import hbold

from database import get_user_async, upsert_user_async
from keyboards.main import main_keyboard, profile_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def handle_start(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    created = await upsert_user_async(user.id, user.username, user.full_name or "")

    if created:
        await message.answer(
            f"Привет, {hbold(user.full_name)}! 🌤\n\n"
            "Я SmartSkyBot — персональный погодный помощник.\n"
            "Сначала выбери, кто ты:",
            reply_markup=profile_keyboard(),
        )
    else:
        info = await get_user_async(user.id)
        profile = info.get("profile_type", "Обычный") if info else "Обычный"
        city = info.get("city", "не указан") if info else "не указан"
        await message.answer(
            f"С возвращением, {hbold(user.full_name)}! 🌤\n\n"
            f"👤 Профиль: {profile}\n"
            f"🏙 Город: {city}\n\n"
            "Нажми «🌤 Погода», чтобы узнать прогноз!",
            reply_markup=main_keyboard(),
        )
