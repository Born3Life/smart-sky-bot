from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter

from database import check_ai_limit_async, get_user_async, increment_ai_usage_async
from keyboards.main import main_keyboard
from services.ai_recommendations import ai_tip
from services.recommendation import fmt_windows
from services.weather_forecast import (
    fetch_day_night,
    fetch_forecast,
    fetch_raw_forecast,
    fmt_day_night,
    fmt_forecast,
    fmt_precipitation,
)
from services.weather_text import fmt_weather
from services.web_search import weather_search
from weather import fetch_by_city, fetch_by_coords, ts_to_time

logger = logging.getLogger(__name__)

router = Router()


async def _get_user_info(
    user_id: int,
) -> dict:
    info = await get_user_async(user_id)
    if not info:
        return {"city": None, "has_children": 0, "workplace": "", "full_name": ""}
    return {
        "city": info.get("city"),
        "has_children": info.get("has_children", 0),
        "workplace": info.get("workplace", ""),
        "full_name": info.get("full_name") or "",
    }


def _precipitation_alert(city: str) -> str | None:
    raw = fetch_raw_forecast(city)
    if not raw:
        return None
    alert = fmt_precipitation(raw)
    return alert if alert and len(alert) > 0 else None


@router.message(F.text == "🌤 Сейчас", StateFilter(None))
@router.message(Command("weather"), StateFilter(None))
async def handle_weather_now(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await _get_user_info(user.id)
    city = info["city"]
    if not city:
        await message.answer("🏙 Сначала укажи город через «🏙 Город».")
        return

    sent = await message.answer("🔍 Получаю данные о погоде...")
    weather = fetch_by_city(city)
    if weather is None:
        await sent.edit_text(f"❌ Не удалось получить погоду для «{city}».")
        return

    weather_block = fmt_weather(weather)
    windows = fmt_windows(city) if city else None
    precip = _precipitation_alert(city)

    output = [weather_block]
    if precip:
        output.append("")
        output.append(f"⚠️ <b>Осадки сегодня:</b>\n{precip}")
    elif windows:
        output.append("")
        output.append("📋 <b>Прогноз на сегодня:</b>")
        output.append(windows)

    name = info["full_name"]
    if name:
        output.append("")
        output.append(f"{name}, хорошего дня! ☀️")

    await sent.edit_text("\n".join(output))
    await message.answer("Выбери действие:", reply_markup=main_keyboard())


@router.message(F.text == "📅 Сегодня", StateFilter(None))
async def handle_today_mini(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await _get_user_info(user.id)
    city = info["city"]
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    weather = fetch_by_city(city)
    if weather is None:
        await message.answer("❌ Нет данных.")
        return

    dn = fetch_day_night(city)
    dn_line = fmt_day_night(dn, "today")
    precip = _precipitation_alert(city)

    lines = [
        f"📅 <b>Сегодня, {city}</b>",
        "",
        f"🌡 {weather.temperature}°C (ощущается {weather.feels_like}°C)",
        f"💧 {weather.humidity}%  💨 {weather.wind_speed} м/с",
        f"📝 {weather.description.capitalize()}",
    ]
    if dn_line:
        lines.append(dn_line)
    if weather.uvi is not None:
        lines.append(f"☀️ UV-индекс: {weather.uvi}")
    if weather.sunrise:
        lines.append(f"🌅 Рассвет: {ts_to_time(weather.sunrise)}")
    if weather.sunset:
        lines.append(f"🌇 Закат: {ts_to_time(weather.sunset)}")
    if precip:
        lines.append("")
        lines.append(f"⚠️ <b>Осадки сегодня:</b>\n{precip}")

    name = info["full_name"]
    if name:
        lines.append("")
        lines.append(f"{name}, хорошего дня! ☀️")

    await message.answer("\n".join(lines))
    await message.answer("Выбери действие:", reply_markup=main_keyboard())


@router.message(F.text == "📅 Завтра", StateFilter(None))
async def handle_tomorrow(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await _get_user_info(user.id)
    city = info["city"]
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    sent = await message.answer("📅 Получаю прогноз на завтра...")
    forecast = fetch_forecast(city)
    if not forecast or len(forecast) < 2:
        weather = fetch_by_city(city)
        if weather:
            name = info["full_name"]
            greeting = f"\n\n{name}, хорошего вечера! 🌙" if name else ""
            await sent.edit_text(
                f"📅 <b>Завтра, {city}</b>\n\n"
                f"🌡 Сейчас {weather.temperature}°C, {weather.description}\n"
                f"💡 Прогноз на завтра временно недоступен.{greeting}"
            )
            await message.answer("Выбери действие:", reply_markup=main_keyboard())
            return
        await sent.edit_text("❌ Нет данных на завтра.")
        return

    f = forecast[1]
    dn = fetch_day_night(city)
    dn_line = fmt_day_night(dn, "tomorrow")
    msg = (
        f"📅 <b>Завтра, {f['date']}</b>\n"
        f"🌡 {f['temp']}°C (ощущается {f['feels_like']}°C)\n"
        f"💧 {f['humidity']}%  💨 {f['wind']} м/с\n"
        f"📝 {f['desc'].capitalize()}\n"
        f"{dn_line}"
    )
    name = info["full_name"]
    if name:
        msg += f"\n\n{name}, готовься заранее! 😊"
    await sent.edit_text(msg)
    await message.answer("Выбери действие:", reply_markup=main_keyboard())


@router.message(F.text == "📅 7 дней", StateFilter(None))
@router.message(Command("forecast"), StateFilter(None))
async def handle_forecast(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await _get_user_info(user.id)
    city = info["city"]
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    sent = await message.answer("📅 Получаю прогноз...")
    forecast = fetch_forecast(city)
    if forecast is None:
        weather = fetch_by_city(city)
        if weather:
            name = info["full_name"]
            greeting = f"\n\n{name}, планируй неделю! 📋" if name else ""
            await sent.edit_text(
                f"📅 <b>Прогноз на неделю, {city}</b>\n\n"
                f"🌡 Сейчас {weather.temperature}°C, {weather.description}\n"
                f"💡 Детальный прогноз временно недоступен.{greeting}"
            )
            await message.answer("Выбери действие:", reply_markup=main_keyboard())
            return
        await sent.edit_text("❌ Нет данных.")
        return

    msg = fmt_forecast(forecast, city)
    name = info["full_name"]
    if name:
        msg += f"\n\n{name}, планируй неделю заранее! 📋"
    await sent.edit_text(msg)
    await message.answer("Выбери действие:", reply_markup=main_keyboard())


@router.message(F.text == "🌅 Рассвет", StateFilter(None))
async def handle_sun(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await _get_user_info(user.id)
    city = info["city"]
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    weather = fetch_by_city(city)
    if weather is None:
        await message.answer("❌ Нет данных.")
        return

    name = info["full_name"]
    day_len: str | None = None
    if weather.sunset and weather.sunrise:
        secs = weather.sunset - weather.sunrise
        hours = secs // 3600
        mins = (secs % 3600) // 60
        day_len = f"{hours}ч {mins}мин"
    msg = (
        f"🌅 <b>{city}</b>\n\n"
        f"🌅 Рассвет: {ts_to_time(weather.sunrise)}\n"
        f"🌇 Закат: {ts_to_time(weather.sunset)}\n"
        f"☀️ Световой день: {day_len or '—'}"
    )
    if name:
        msg += f"\n\n{name}, хорошего дня! ☀️"
    await message.answer(msg)


@router.message(F.text == "☀️ UV-индекс", StateFilter(None))
async def handle_uv(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await _get_user_info(user.id)
    city = info["city"]
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
    name = info["full_name"]
    msg = (
        f"☀️ <b>UV-индекс в {city}</b>\n\n"
        f"Значение: {weather.uvi}\n"
        f"Риск: {risk}\n\n"
        f"{uv_advice}"
    )
    if name:
        msg += f"\n\n{name}, береги кожу! 🧴"
    await message.answer(msg)


@router.message(F.text == "🤖 AI Совет", StateFilter(None))
async def handle_ai_tip(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await _get_user_info(user.id)
    city = info["city"]
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    allowed, remaining = await check_ai_limit_async(user.id)
    if not allowed:
        await message.answer(
            "🤖 <b>Лимит бесплатных AI-советов на сегодня исчерпан</b>\n\n"
            "Получи неограниченные советы с Premium:\n"
            "💎 /subscribe — 50⭐/мес, пробный период 2 дня",
        )
        return

    weather = fetch_by_city(city)
    if weather is None:
        await message.answer("❌ Нет данных о погоде.")
        return

    sent = await message.answer("🤖 Думаю...")
    tip = ai_tip(
        info["has_children"], info["workplace"], weather, city,
        user_id=user.id, user_name=info["full_name"],
    )
    await increment_ai_usage_async(user.id)

    precip = _precipitation_alert(city)
    name = info["full_name"]

    output = [
        f"🤖 <b>AI-рекомендация</b>\n"
        f"🏙 {city} | {weather.description.capitalize()}, {weather.temperature}°C",
    ]

    if precip:
        output.append("")
        output.append(f"⚠️ <b>Осадки сегодня:</b>\n{precip}")

    if tip:
        output.append("")
        output.append(tip)
    else:
        output.append("")
        output.append(f"💡 {weather.description.capitalize()}, {weather.temperature}°C. Ветер {weather.wind_speed} м/с.")

    if name:
        output.append("")
        output.append(f"{name}, хорошего дня! ☀️")

    if remaining <= 1:
        output.append("")
        output.append("💡 Бесплатных советов больше нет. 💎 /subscribe для Premium")

    await sent.edit_text("\n".join(output))


@router.message(F.text == "🔍 Поиск", StateFilter(None))
async def handle_search(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await _get_user_info(user.id)
    city = info["city"]
    if not city:
        await message.answer("🏙 Сначала укажи город.")
        return

    sent = await message.answer(f"🔍 Ищу «погода {city}»...")
    results = weather_search(city)

    if not results:
        await sent.edit_text("❌ Ничего не найдено.")
        return

    lines = [f"🔍 <b>Результаты поиска: {city}</b>\n"]
    for r in results:
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")
        lines.append(f"▫️ <b>{title}</b>")
        if snippet:
            lines.append(f"   {snippet[:200]}")
        if link and not link.startswith("http"):
            link = ""
        if link:
            lines.append(f"   🔗 {link}")

    await sent.edit_text("\n".join(lines))
    await message.answer("Выбери действие:", reply_markup=main_keyboard())


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

    info = await _get_user_info(user.id)
    city = weather.city_name if weather else info["city"]
    name = info["full_name"]

    weather_block = fmt_weather(weather)
    windows = fmt_windows(city) if city else None
    output = [weather_block]
    if windows:
        output.append("")
        output.append(windows)
    if name:
        output.append("")
        output.append(f"{name}, хорошего дня! ☀️")

    await sent.edit_text("\n".join(output))
    await message.answer("Выбери действие:", reply_markup=main_keyboard())
