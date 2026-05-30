from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter

from database import get_user_async
from keyboards.main import main_keyboard
from services.ai_recommendations import ai_tip
from services.recommendation import get_recommendations
from services.weather_forecast import fetch_forecast, fmt_forecast
from services.weather_text import fmt_weather
from weather import fetch_by_city, fetch_by_coords, ts_to_time

logger = logging.getLogger(__name__)

router = Router()


async def _get_city_profile(
    user_id: int,
) -> tuple[str | None, str | None]:
    info = await get_user_async(user_id)
    if not info:
        return None, None
    return info.get("city"), info.get("profile_type", "Обычный")


async def _weather_or_prompt(
    message: types.Message,
    sent: types.Message,
    city: str,
    profile: str,
) -> None:
    weather = fetch_by_city(city)
    if weather is None:
        await sent.edit_text(
            f"❌ Не удалось получить погоду для «{city}».\n"
            "Проверь название города или попробуй позже.",
        )
        return

    weather_block = fmt_weather(weather)
    recs = get_recommendations(profile, weather, city)
    rec_lines = "\n".join(f"• {r}" for r in recs)

    await sent.edit_text(
        f"{weather_block}\n\n👤 <b>Рекомендации для «{profile}»:</b>\n{rec_lines}"
    )
    await message.answer("Выбери действие:", reply_markup=main_keyboard())


@router.message(F.text == "🌤 Сейчас", StateFilter(None))
@router.message(Command("weather"), StateFilter(None))
async def handle_weather_now(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, profile = await _get_city_profile(user.id)
    if not city:
        await message.answer("🏙 Сначала укажи город через «🏙 Город».")
        return
    if profile is None:
        await message.answer("Напиши /start, чтобы зарегистрироваться")
        return

    sent = await message.answer("🔍 Получаю данные о погоде...")
    await _weather_or_prompt(message, sent, city, profile)


@router.message(F.text == "📅 Сегодня", StateFilter(None))
async def handle_today_mini(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, profile = await _get_city_profile(user.id)
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return
    if profile is None:
        return

    weather = fetch_by_city(city)
    if weather is None:
        await message.answer("❌ Нет данных.")
        return

    lines = [
        f"📅 <b>Сегодня, {city}</b>",
        "",
        f"🌡 {weather.temperature}°C (ощущается {weather.feels_like}°C)",
        f"💧 {weather.humidity}%  💨 {weather.wind_speed} м/с",
        f"📝 {weather.description.capitalize()}",
    ]
    if weather.uvi is not None:
        lines.append(f"☀️ UV-индекс: {weather.uvi}")
    if weather.sunrise:
        lines.append(f"🌅 Рассвет: {ts_to_time(weather.sunrise)}")
    if weather.sunset:
        lines.append(f"🌇 Закат: {ts_to_time(weather.sunset)}")
    lines.append("")
    recs = get_recommendations(profile, weather, city)
    lines.extend(f"• {r}" for r in recs[:2])

    await message.answer("\n".join(lines))
    await message.answer("Выбери действие:", reply_markup=main_keyboard())


@router.message(F.text == "📅 Завтра", StateFilter(None))
async def handle_tomorrow(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, _ = await _get_city_profile(user.id)
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    forecast = fetch_forecast(city)
    if not forecast or len(forecast) < 2:
        await message.answer("❌ Нет данных на завтра.")
        return

    f = forecast[1]
    await message.answer(
        f"📅 <b>Завтра, {f['date']}</b>\n"
        f"🌡 {f['temp']}°C (ощущается {f['feels_like']}°C)\n"
        f"💧 {f['humidity']}%  💨 {f['wind']} м/с\n"
        f"📝 {f['desc'].capitalize()}"
    )
    await message.answer("Выбери действие:", reply_markup=main_keyboard())


@router.message(F.text == "📅 7 дней", StateFilter(None))
@router.message(Command("forecast"), StateFilter(None))
async def handle_forecast(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, _ = await _get_city_profile(user.id)
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    sent = await message.answer("📅 Получаю прогноз...")
    forecast = fetch_forecast(city)
    if forecast is None:
        await sent.edit_text("❌ Нет данных.")
        return

    await sent.edit_text(fmt_forecast(forecast))
    await message.answer("Выбери действие:", reply_markup=main_keyboard())


@router.message(F.text == "🌅 Рассвет", StateFilter(None))
async def handle_sun(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, _ = await _get_city_profile(user.id)
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    weather = fetch_by_city(city)
    if weather is None:
        await message.answer("❌ Нет данных.")
        return

    day_len: str | None = None
    if weather.sunset and weather.sunrise:
        day_len = f"{weather.sunset - weather.sunrise} сек"
    await message.answer(
        f"🌅 <b>{city}</b>\n\n"
        f"🌅 Рассвет: {ts_to_time(weather.sunrise)}\n"
        f"🌇 Закат: {ts_to_time(weather.sunset)}\n"
        f"☀️ Световой день: {day_len or '—'}"
    )


@router.message(F.text == "☀️ UV-индекс", StateFilter(None))
async def handle_uv(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, _ = await _get_city_profile(user.id)
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    weather = fetch_by_city(city)
    if weather is None or weather.uvi is None:
        await message.answer("❌ Нет данных об UV.")
        return

    risk = (
        "низкий"
        if weather.uvi < 3
        else "умеренный"
        if weather.uvi < 6
        else "высокий"
        if weather.uvi < 8
        else "очень высокий"
    )
    uv_advice = (
        "🕶 Нужны солнцезащитные очки и крем" if weather.uvi > 3 else "✅ UV-безопасно"
    )
    await message.answer(
        f"☀️ <b>UV-индекс в {city}</b>\n\n"
        f"Значение: {weather.uvi}\n"
        f"Риск: {risk}\n\n"
        f"{uv_advice}"
    )


@router.message(F.text == "🤖 AI Совет", StateFilter(None))
async def handle_ai_tip(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    city, profile = await _get_city_profile(user.id)
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return
    if profile is None:
        return

    weather = fetch_by_city(city)
    if weather is None:
        await message.answer("❌ Нет данных о погоде.")
        return

    sent = await message.answer("🤖 Думаю...")
    tip = ai_tip(profile, weather)
    if tip:
        await sent.edit_text(
            f"🤖 <b>AI-рекомендации для «{profile}»</b>\n\n"
            f"🏙 {city} | {weather.description.capitalize()}\n"
            f"🌡 {weather.temperature}°C\n\n"
            f"{tip}"
        )
    else:
        await sent.edit_text("❌ Не удалось получить AI-рекомендацию. Попробуй позже.")


@router.message(F.location, StateFilter(None))
async def handle_location(message: types.Message) -> None:
    user = message.from_user
    if user is None or message.location is None:
        return

    lat = message.location.latitude
    lon = message.location.longitude

    sent = await message.answer("📍 Получаю погоду по координатам...")
    weather = fetch_by_coords(lat, lon)
    if weather is None:
        await sent.edit_text("❌ Не удалось получить погоду.")
        return

    profile = "Обычный"
    city, p = await _get_city_profile(user.id)
    if p:
        profile = p

    recs = get_recommendations(profile, weather, city)
    rec_lines = "\n".join(f"• {r}" for r in recs)

    rec_text = f"\n\n👤 <b>Рекомендации для «{profile}»:</b>\n{rec_lines}"
    await sent.edit_text(f"{fmt_weather(weather)}{rec_text}")
    await message.answer("Выбери действие:", reply_markup=main_keyboard())
