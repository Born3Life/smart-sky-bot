from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from database import update_city_async, update_profile_fields_async
from keyboards.main import main_keyboard, workplace_keyboard
from models.states import Onboarding
from weather import fetch_by_city

logger = logging.getLogger(__name__)

router = Router()


@router.message(Onboarding.waiting_name)
async def onboarding_name(message: types.Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Напиши, как тебя зовут:")
        return
    user = message.from_user
    if user is not None:
        await update_profile_fields_async(user.id, full_name=name)
    await state.update_data(name=name)
    await state.set_state(Onboarding.waiting_children)
    await message.answer(f"Приятно познакомиться, {name}! 👋\n\nЕсть ли маленькие дети? (Да / Нет)")


@router.message(Onboarding.waiting_children)
async def onboarding_children(message: types.Message, state: FSMContext) -> None:
    val = (message.text or "").strip().lower()
    if val not in ("да", "есть", "yes", "1", "нет", "не", "no", "0"):
        await message.answer("Ответь «Да» или «Нет»:")
        return
    has_children = 1 if val in ("да", "есть", "yes", "1") else 0
    user = message.from_user
    if user is not None:
        await update_profile_fields_async(user.id, has_children=has_children)
    await state.update_data(has_children=has_children)
    await state.set_state(Onboarding.waiting_workplace)
    await message.answer(
        "Где ты работаешь?",
        reply_markup=workplace_keyboard(),
    )


@router.message(Onboarding.waiting_workplace)
async def onboarding_workplace(message: types.Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text not in ("🏗 На улице", "🏢 В здании", "на улице", "в здании"):
        await message.answer("Выбери вариант на клавиатуре 👇", reply_markup=workplace_keyboard())
        return
    workplace = "на улице" if "улице" in text else "в здании"
    user = message.from_user
    if user is not None:
        await update_profile_fields_async(user.id, workplace=workplace)
    await state.update_data(workplace=workplace)
    await state.set_state(Onboarding.waiting_city)
    await message.answer(
        "В каком городе ты проживаешь?\n(Например: Москва, Северск)",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@router.message(Onboarding.waiting_city)
async def onboarding_city(message: types.Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None or not message.text:
        return

    city = message.text.strip()
    weather = fetch_by_city(city)
    if weather is None:
        await message.answer(f"❌ Город «{city}» не найден. Попробуй ещё раз:")
        return

    await update_city_async(user.id, city)
    data = await state.get_data()
    name = data.get("name", user.full_name or "друг")
    children = "Да" if data.get("has_children") else "Нет"
    workplace = data.get("workplace", "")
    await state.clear()

    await message.answer(
        f"✅ Готово, {name}!\n\n"
        f"🏙 Город: {city}\n"
        f"👶 Маленькие дети: {children}\n"
        f"💼 Работа: {workplace}\n\n"
        "Теперь я могу давать персональные советы по погоде!",
        reply_markup=main_keyboard(),
    )
