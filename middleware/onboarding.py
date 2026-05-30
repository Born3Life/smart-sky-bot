from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from services.profile_check import is_profile_complete

logger = logging.getLogger(__name__)

_ONBOARDING_BUTTONS = {
    "/start",
}


class OnboardingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        text = event.text.strip()
        if text in _ONBOARDING_BUTTONS:
            return await handler(event, data)

        # Allow messages during FSM (onboarding flow)
        state = data.get("state")
        if state is not None:
            current = await state.get_state()
            if current is not None and current.startswith("Onboarding"):
                return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return await handler(event, data)

        if not is_profile_complete(user_id):
            await event.answer(
                "👋 Сначала заполни профиль — напиши /start",
            )
            return

        return await handler(event, data)
