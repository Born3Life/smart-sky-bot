from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌤 Сейчас")],
            [
                KeyboardButton(text="📅 Сегодня"),
                KeyboardButton(text="📅 Завтра"),
                KeyboardButton(text="📅 7 дней"),
            ],
            [
                KeyboardButton(text="🌅 Рассвет"),
                KeyboardButton(text="☀️ UV-индекс"),
                KeyboardButton(text="🤖 AI Совет"),
            ],
            [
                KeyboardButton(text="📍 Погода здесь", request_location=True),
            ],
            [
                KeyboardButton(text="👤 Профиль"),
                KeyboardButton(text="✏️ Изменить профиль"),
            ],
            [
                KeyboardButton(text="🏙 Город"),
                KeyboardButton(text="💎 Премиум"),
            ],
            [
                KeyboardButton(text="🔍 Поиск"),
            ],
        ],
        resize_keyboard=True,
    )


def workplace_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏗 На улице")],
            [KeyboardButton(text="🏢 В здании")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
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
            [KeyboardButton(text="🏃 Спортсмен")],
            [KeyboardButton(text="🤧 Аллергик")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
