from __future__ import annotations

from os import getenv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def bot_token() -> str:
    token = getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set")
    return token


def openweather_api_key() -> str | None:
    return getenv("OPENWEATHER_API_KEY")


def openrouter_api_key() -> str | None:
    return getenv("OPENROUTER_API_KEY")


def telegram_proxy() -> str | None:
    return getenv("TELEGRAM_PROXY")
