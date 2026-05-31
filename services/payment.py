from __future__ import annotations

from aiogram import Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery, SuccessfulPayment

STARS_PRICE = 50
MONTHS = 1


def stars_invoice() -> tuple[str, str, list[LabeledPrice]]:
    title = "SmartSky Premium — 1 месяц"
    description = (
        "🌟 Прогноз на 7 дней\n"
        "🌟 AI-рекомендации\n"
        "🌟 Уведомления\n"
        "🌟 UV-индекс и рассвет"
    )
    prices = [LabeledPrice(label="Premium 1мес", amount=STARS_PRICE)]
    return title, description, prices


async def send_stars_invoice(bot: Bot, user_id: int) -> None:
    title, desc, prices = stars_invoice()
    await bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=desc,
        payload=f"premium_{user_id}_{MONTHS}m",
        provider_token="",
        currency="XTR",
        prices=prices,
    )


async def handle_pre_checkout(
    pre_checkout_query: PreCheckoutQuery,
    bot: Bot,
) -> None:
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


async def handle_successful_payment(
    message: SuccessfulPayment,
    user_id: int,
    bot: Bot,
) -> str:
    from database import set_premium_async

    days = 30
    await set_premium_async(user_id, days)
    return (
        "💎 <b>Premium активирован!</b>\n\n"
        f"Спасибо за покупку! 🎉\n"
        f"Длительность: {days} дней\n"
        "Тебе доступны все премиум-функции!"
    )
