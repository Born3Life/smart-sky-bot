from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from database import get_user

logger = logging.getLogger(__name__)


PREMIUM_FEATURES = [
    "/subscribe",
    "/forecast",
    "/ai_tip",
    "/notifications",
]


class PremiumMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        text = event.text.strip()
        is_premium_cmd = any(text.startswith(f) for f in PREMIUM_FEATURES)
        if not is_premium_cmd:
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return await handler(event, data)

        user = get_user(user_id)
        if user is None:
            return await handler(event, data)

        is_premium = user.get("is_premium", False)
        premium_until = user.get("premium_until")

        if is_premium and premium_until:
            try:
                until = datetime.fromisoformat(premium_until)
                if datetime.utcnow() > until:
                    is_premium = False
            except (ValueError, TypeError):
                is_premium = False

        if not is_premium:
            await event.answer(
                "💎 Это премиум-функция.\n\n"
                "Оформи подписку — /subscribe\n"
                "Пробный период 7 дней бесплатно!",
            )
            return

        return await handler(event, data)
