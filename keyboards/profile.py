from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models import PROFILES


def profile_selection_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"profile:{name}")]
        for name in PROFILES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
