from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import StateFilter

from database import get_user_async, update_profile_async
from keyboards.main import main_keyboard
from models import PROFILE_BUTTONS

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "🔙 Назад", StateFilter(None))
async def handle_back(message: types.Message) -> None:
    await message.answer("Главное меню:", reply_markup=main_keyboard())


@router.message(F.text.in_(list(PROFILE_BUTTONS)), StateFilter(None))
async def handle_profile_selection(message: types.Message) -> None:
    user = message.from_user
    if user is None or not message.text:
        return

    profile = PROFILE_BUTTONS[message.text.strip()]
    await update_profile_async(user.id, profile)

    info = await get_user_async(user.id)
    city = info.get("city") if info else None

    if city:
        await message.answer(
            f"✅ Профиль: <b>{profile}</b>\n"
            f"🏙 Город: {city}\n\n"
            "Нажми «🌤 Сейчас» для прогноза!",
            reply_markup=main_keyboard(),
        )
    else:
        await message.answer(
            f"✅ Профиль: <b>{profile}</b>\n\n"
            "Теперь напиши название своего города\n"
            "(например: Москва, Санкт-Петербург):",
        )


@router.message(F.text == "👤 Профиль")
async def handle_show_profile(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await get_user_async(user.id)
    if not info:
        await message.answer("Напиши /start, чтобы зарегистрироваться")
        return

    profile = info.get("profile_type", "Обычный")
    await message.answer(
        f"👤 <b>Твой профиль:</b> {profile}\n\n"
        "Чтобы сменить — просто напиши название нового профиля:\n"
        "Строитель, Водитель, Родитель, Дачник, Рыбак, Обычный, Спортсмен, Аллергик",
    )
