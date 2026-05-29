from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌤 Погода")],
            [
                KeyboardButton(text="👤 Профиль"),
                KeyboardButton(text="🏙 Изменить город"),
            ],
        ],
        resize_keyboard=True,
    )


def profile_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👷 Строитель")],
            [KeyboardButton(text="🚗 Водитель")],
            [KeyboardButton(text="👨‍👩‍👧‍👦 Родитель")],
            [KeyboardButton(text="🌱 Дачник")],
            [KeyboardButton(text="🎣 Рыбак")],
            [KeyboardButton(text="👤 Обычный")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
