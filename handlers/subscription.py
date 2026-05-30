from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter

from database import (
    activate_trial_async,
    get_user_async,
)
from services.payment import (
    handle_pre_checkout,
    handle_successful_payment,
    send_stars_invoice,
)

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("subscribe"), StateFilter(None))
@router.message(F.text == "💎 Премиум", StateFilter(None))
async def handle_subscribe(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await get_user_async(user.id)
    if not info:
        await message.answer("Напиши /start, чтобы зарегистрироваться")
        return

    is_premium = info.get("is_premium")
    premium_until = info.get("premium_until")

    if is_premium and premium_until:
        try:
            until = datetime.fromisoformat(premium_until)
            days_left = (until - datetime.utcnow()).days
            if days_left > 0:
                await message.answer(
                    f"💎 У тебя уже есть Premium!\n"
                    f"Действует до: {premium_until[:10]}\n"
                    f"Осталось дней: {days_left}",
                )
                return
        except (ValueError, TypeError):
            pass

    text = (
        "💎 <b>SmartSky Premium</b>\n\n"
        "— 🌤 Прогноз на 7 дней\n"
        "— 🤖 AI-рекомендации\n"
        "— ☀️ UV-индекс\n"
        "— 🔔 Ежедневные уведомления\n"
        "— 📍 Несколько городов\n\n"
        "💰 <b>50 ⭐ Telegram Stars / месяц</b>\n\n"
        "Попробуй 2 дня бесплатно! 👇"
    )

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🎁 2 дня бесплатно",
                    callback_data="trial",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="💳 Купить 50⭐",
                    callback_data="buy_stars",
                ),
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
            "2 дня Premium бесплатно.\n"
            "Наслаждайся всеми функциями! 🌤",
        )
    else:
        await callback.message.edit_text(
            "💎 У тебя уже есть Premium!\nПродление через /subscribe.",
        )
    await callback.answer()


@router.callback_query(F.data == "buy_stars")
async def handle_buy_stars(callback: types.CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return

    bot = callback.bot
    await callback.answer("Отправляю счёт...")

    try:
        await send_stars_invoice(bot, user.id)
    except Exception:
        await callback.message.answer(
            "❌ Ошибка оплаты. Убедись, что в @BotFather "
            "подключены платежи (Payments → Telegram Stars).\n"
            "Или активируй 7 дней бесплатно.",
        )


@router.pre_checkout_query()
async def pre_checkout_handler(
    pre_checkout_query: types.PreCheckoutQuery,
) -> None:
    await handle_pre_checkout(pre_checkout_query, pre_checkout_query.bot)


@router.message(F.successful_payment, StateFilter(None))
async def payment_success(message: types.Message) -> None:
    user = message.from_user
    if user is None or message.successful_payment is None:
        return

    reply = await handle_successful_payment(
        message.successful_payment,
        user.id,
        message.bot,
    )
    await message.answer(reply)
