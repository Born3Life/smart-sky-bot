from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    waiting_name = State()
    waiting_profile = State()
    waiting_city = State()


class EditProfile(StatesGroup):
    waiting_field = State()
