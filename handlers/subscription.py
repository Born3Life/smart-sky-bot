from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import Command

from database import (
    activate_trial_async,
    get_user_async,
)

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("subscribe"))
@router.message(F.text == "💎 Премиум")
async def handle_subscribe(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await get_user_async(user.id)
    if not info:
        await message.answer("Напиши /start, чтобы зарегистрироваться")
        return

    is_premium = info.get("is_premium", False)
    premium_until = info.get("premium_until")

    if is_premium and premium_until:
        try:
            until = datetime.fromisoformat(premium_until)
            days_left = (until - datetime.utcnow()).days
            if days_left > 0:
                await message.answer(
                    f"💎 У тебя уже есть Premium!\n"
                    f"Действует до: {until[:10]}\n"
                    f"Осталось дней: {days_left}",
                )
                return
        except (ValueError, TypeError):
            pass

    text = (
        "💎 <b>SmartSky Premium</b>\n\n"
        "— 🌤 Прогноз на 7 дней\n"
        "— 🤖 AI-рекомендации (OpenRouter)\n"
        "— 🔔 Ежедневные уведомления\n"
        "— 📍 Несколько городов\n"
        "— ⚠️ Опасные погодные алерты\n\n"
        "💰 <b>50 ⭐ / месяц</b> (~100₽)\n"
        "🚀 Можно оплатить через Telegram Stars\n\n"
        "Попробуй 7 дней бесплатно 👇"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🎁 7 дней бесплатно", callback_data="trial"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="💳 Купить 50⭐", callback_data="buy_stars"
                )
            ],
        ],
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "trial")
async def handle_trial(callback: types.CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return

    activated = await activate_trial_async(user.id)
    if activated:
        await callback.message.edit_text(
            "🎁 <b>Пробный период активирован!</b>\n\n"
            "7 дней Premium бесплатно.\n"
            "Наслаждайся всеми функциями! 🌤",
        )
    else:
        await callback.message.edit_text(
            "💎 У тебя уже есть Premium!\nПродление можно оформить через /subscribe.",
        )
    await callback.answer()


@router.callback_query(F.data == "buy_stars")
async def handle_buy_stars(callback: types.CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return

    # TODO: Telegram Stars invoice
    # Requires connected payment provider in @BotFather
    await callback.message.edit_text(
        "💳 Оплата через Telegram Stars будет доступна после "
        "подключения платежей в @BotFather.\n\n"
        "А пока — активируй 7 дней бесплатно!",
    )
    await callback.answer()
