# SmartSkyBot 🌤

Персональный погодный помощник в Telegram.
Погода через Gismeteo (основной) + OpenWeather (fallback).
AI-рекомендации, профильные советы, Telegram Stars.

## Быстрый старт

```bash
git clone https://github.com/Born3Life/smart-sky-bot.git
cd smart-sky-bot
uv sync --no-dev
cp .env.example .env  # заполни токены
uv run python bot.py
```

## Переменные окружения (.env)

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен от @BotFather |
| `OPENWEATHER_API_KEY` | Ключ OpenWeather (fallback) |
| `OPENROUTER_API_KEY` | Ключ OpenRouter (AI-советы) |
| `TELEGRAM_PROXY` | Прокси для Telegram (опционально) |

## Деплой на Render

1. Связать GitHub репозиторий с Render Web Service
2. Build: `uv sync --no-dev`
3. Start: `uv run python bot.py`
4. Установить `BOT_TOKEN`, `OPENWEATHER_API_KEY`, `OPENROUTER_API_KEY` в Dashboard
