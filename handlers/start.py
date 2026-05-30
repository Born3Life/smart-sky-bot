from __future__ import annotations

import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import get_user_async, upsert_user_async
from keyboards.main import main_keyboard
from models.states import Onboarding

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def handle_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user is None:
        return

    created = await upsert_user_async(user.id, user.username, user.full_name or "")

    if created:
        await state.set_state(Onboarding.waiting_name)
        await message.answer(
            "👋 <b>Привет! Я SmartSkyBot</b> — твой персональный\n"
            "погодный помощник 🌤\n\n"
            "Я знаю погоду в любом городе мира, даю советы по погоде\n"
            "под твой профиль и помогаю планировать день.\n\n"
            "Для начала давай познакомимся!\n\n"
            "<b>Как тебя зовут?</b>",
        )
        return

    info = await get_user_async(user.id)
    profile = info.get("profile_type", "Обычный") if info else "Обычный"
    city = info.get("city") if info else None
    fallback = user.full_name or ""
    name = info.get("full_name", fallback) if info else fallback

    if city:
        await message.answer(
            f"С возвращением, {name}! 🌤\n\n"
            f"👤 Профиль: {profile}\n"
            f"🏙 Город: {city}\n\n"
            "Нажми «🌤 Сейчас», чтобы узнать погоду!",
            reply_markup=main_keyboard(),
        )
    else:
        await state.set_state(Onboarding.waiting_city)
        await message.answer(
            f"С возвращением, {name}!\n\n"
            "У тебя ещё не указан город.\n"
            "Напиши название (например: Москва, Лондон):",
        )
