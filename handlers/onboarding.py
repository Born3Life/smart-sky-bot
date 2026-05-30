from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from database import update_city_async, update_profile_async
from keyboards.main import main_keyboard, profile_keyboard
from models import PROFILE_BUTTONS
from models.states import Onboarding
from weather import fetch_by_city

logger = logging.getLogger(__name__)

router = Router()


@router.message(Onboarding.waiting_name)
async def onboarding_name(message: types.Message, state: FSMContext) -> None:
    name = message.text.strip() if message.text else "друг"
    await state.update_data(name=name)
    await state.set_state(Onboarding.waiting_profile)

    await message.answer(
        f"Очень приятно, {name}! 🤗\n\n"
        "Теперь расскажи, чем ты занимаешься,\n"
        "чтобы я мог давать самые полезные советы:",
        reply_markup=profile_keyboard(),
    )


@router.message(Onboarding.waiting_profile, F.text.in_(list(PROFILE_BUTTONS)))
async def onboarding_profile(message: types.Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None or not message.text:
        return

    profile = PROFILE_BUTTONS[message.text.strip()]
    await update_profile_async(user.id, profile)
    await state.update_data(profile=profile)
    await state.set_state(Onboarding.waiting_city)

    await message.answer(
        f"Отлично, {profile}! 👌\n\n"
        "А в каком городе ты находишься?\n"
        "Напиши название (например: Москва, Лондон):",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@router.message(Onboarding.waiting_profile)
async def onboarding_profile_invalid(message: types.Message) -> None:
    await message.answer(
        "Пожалуйста, выбери один из вариантов на клавиатуре 👇",
        reply_markup=profile_keyboard(),
    )


@router.message(Onboarding.waiting_city)
async def onboarding_city(message: types.Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None or not message.text:
        await message.answer("Напиши название города текстом:")
        return

    city = message.text.strip()
    weather = fetch_by_city(city)
    if weather is None:
        await message.answer(
            f"❌ Город «{city}» не найден.\nПроверь название и попробуй ещё раз:",
        )
        return

    await update_city_async(user.id, city)
    data = await state.get_data()
    name = data.get("name", user.full_name or "друг")
    profile = data.get("profile", "Обычный")
    await state.clear()

    await message.answer(
        f"✅ Всё готово, {name}!\n\n"
        f"👤 Профиль: {profile}\n"
        f"🏙 Город: {city}\n\n"
        "Вот что я умею:",
        reply_markup=main_keyboard(),
    )

    await message.answer(
        "🌤 <b>Погода сейчас</b> — температура, ветер, влажность\n"
        "📅 <b>Сегодня / Завтра</b> — краткий прогноз\n"
        "🌅 <b>Рассвет / Закат</b> — время восхода\n"
        "☀️ <b>UV-индекс</b> — уровень солнечной активности\n"
        "📍 <b>Погода здесь</b> — по геолокации\n"
        "👤 <b>Профиль</b> — 8 профилей с советами\n\n"
        "Просто нажимай на кнопки! 👇",
    )

    await message.answer(
        "🌟 <b>SmartSky Premium</b> — ещё больше возможностей!\n\n"
        "— 📅 Прогноз на 7 дней\n"
        "— 🤖 AI-рекомендации\n"
        "— 🔔 Ежедневные уведомления\n\n"
        "💰 Всего <b>50 ⭐ Telegram Stars / месяц</b>\n\n"
        "Попробуй 7 дней бесплатно! 👇",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🎁 7 дней бесплатно",
                        callback_data="trial",
                    ),
                ],
                [
                    types.InlineKeyboardButton(
                        text="💳 Купить 50⭐",
                        callback_data="buy_stars",
                    ),
                ],
                [
                    types.InlineKeyboardButton(
                        text="🔜 Позже",
                        callback_data="later",
                    ),
                ],
            ],
        ),
    )


@router.callback_query(F.data == "later")
async def handle_later(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        "Хорошо! Если надумаешь — нажми «💎 Премиум» в меню 🚀",
    )
    await callback.answer()
