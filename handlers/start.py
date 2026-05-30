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

    await upsert_user_async(user.id, user.username, user.full_name or "")

    await state.set_state(Onboarding.waiting_name)
    await message.answer(
        "👋 <b>Привет! Я SmartSkyBot</b> — твой погодный помощник 🌤\n\n"
        "Давай заполним твой профиль по порядку.\n\n"
        "<b>Как тебя зовут?</b>",
    )
