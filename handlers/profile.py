from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database import get_user_async, update_city_async, update_profile_fields_async
from keyboards.main import main_keyboard
from models import PROFILE_BUTTONS
from models.states import EditProfile
from weather import fetch_by_city

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "🔙 Назад", StateFilter(None))
async def handle_back(message: types.Message) -> None:
    await message.answer("Главное меню:", reply_markup=main_keyboard())


@router.message(EditProfile.waiting_field)
async def handle_edit_field_value(message: types.Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return

    data = await state.get_data()
    field = data.get("field")

    if not field or not message.text:
        await state.clear()
        await message.answer("❌ Ошибка", reply_markup=main_keyboard())
        return

    val: str | int = message.text.strip()

    if field == "has_children":
        if val.lower() in ("да", "есть", "yes", "1"):
            val = 1
        elif val.lower() in ("нет", "не", "no", "0"):
            val = 0
        else:
            await message.answer("Ответь «Да» или «Нет»:")
            return

    if field == "city":
        weather = fetch_by_city(val)
        if weather is None:
            await message.answer(
                f"❌ Город «{val}» не найден.\nПроверь название:",
            )
            return
        await update_city_async(user.id, val)
    else:
        await update_profile_fields_async(user.id, **{field: val})

    await state.clear()

    field_names = {
        "full_name": "Имя",
        "workplace": "Место работы",
        "has_children": "Дети",
        "city": "Город",
    }
    name = field_names.get(field, field)
    await message.answer(
        f"✅ {name} обновлён!",
        reply_markup=main_keyboard(),
    )


PROFILE_EDIT_FIELDS: list[tuple[str, str, str]] = [
    ("full_name", "✏️ Имя", ""),
    ("workplace", "💼 Работа", ""),
    ("has_children", "👶 Дети", ""),
]


@router.message(F.text == "✏️ Изменить профиль", StateFilter(None))
async def handle_edit_profile(message: types.Message, state: FSMContext) -> None:
    await state.set_state(EditProfile.waiting_field)
    await state.update_data(field="full_name")
    await message.answer("Напиши своё имя:")


@router.message(F.text == "👤 Профиль", StateFilter(None))
async def handle_show_profile(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await get_user_async(user.id)
    if not info:
        await message.answer("Напиши /start, чтобы зарегистрироваться")
        return

    name = info.get("full_name") or info.get("username") or "—"
    profile = info.get("profile_type", "Обычный")
    city = info.get("city") or "—"
    workplace = info.get("workplace") or "—"
    has_children = "Да" if info.get("has_children") else "Нет"

    text = (
        f"👤 <b>Твой профиль</b>\n\n"
        f"🧑 Имя: {name}\n"
        f"🏙 Город: {city}\n"
        f"📋 Тип: {profile}\n"
        f"💼 Работа: {workplace}\n"
        f"👶 Дети: {has_children}\n\n"
        f"Изменить данные — нажми на кнопку ниже 👇"
    )

    buttons = [
        [
            types.InlineKeyboardButton(
                text="✏️ Имя",
                callback_data="edit_full_name",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="✏️ Город",
                callback_data="edit_city",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="✏️ Тип профиля",
                callback_data="edit_profile_type",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="✏️ Работа",
                callback_data="edit_workplace",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="✏️ Дети (да/нет)",
                callback_data="edit_has_children",
            )
        ],
    ]

    await message.answer(
        text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("edit_"))
async def handle_edit_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> None:
    field = callback.data.removeprefix("edit_")

    prompts = {
        "full_name": "Напиши своё имя:",
        "city": "Напиши название города:",
        "profile_type": "Выбери тип профиля:",
        "workplace": "Где ты работаешь?",
        "has_children": "У тебя есть дети? (Да/Нет)",
    }

    prompt = prompts.get(field)
    if not prompt:
        await callback.answer("Неизвестное поле")
        return

    await state.set_state(EditProfile.waiting_field)
    await state.update_data(field=field)

    await callback.message.answer(prompt)
    await callback.answer()


@router.message(F.text.in_(list(PROFILE_BUTTONS)), StateFilter(None))
async def handle_profile_selection(message: types.Message) -> None:
    user = message.from_user
    if user is None or not message.text:
        return

    profile = PROFILE_BUTTONS[message.text.strip()]
    await update_profile_fields_async(user.id, profile_type=profile)

    info = await get_user_async(user.id)
    city = info.get("city") if info else None

    if city:
        await message.answer(
            f"✅ Профиль: <b>{profile}</b>\n"
            f"🏙 Город: {city}\n\n"
            "Нажми «🌤 Сейчас» для прогноза!",
            reply_markup=main_keyboard(),
        )
    else:
        await message.answer(
            f"✅ Профиль: <b>{profile}</b>\n\n"
            "Теперь напиши название своего города\n"
            "(например: Москва, Санкт-Петербург):",
        )
