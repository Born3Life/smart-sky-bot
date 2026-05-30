from __future__ import annotations

from models import WeatherData
from services.gismeteo import gismeteo_url
from utils import celsius_to_symbol, fmt_float, wind_description


def fmt_weather(weather: WeatherData) -> str:
    temp_symbol = celsius_to_symbol(weather.temperature)
    wind_desc = wind_description(weather.wind_speed)

    lines = [
        f"🌤 <b>Погода в {weather.city_name}</b>",
        "",
        f"{temp_symbol} <b>Температура:</b> {fmt_float(weather.temperature, '°C')}",
        f"🤷‍♂️ Ощущается как: {fmt_float(weather.feels_like, '°C')}",
        f"💧 Влажность: {weather.humidity}%",
        f"💨 Ветер: {fmt_float(weather.wind_speed, ' м/с')} ({wind_desc})",
    ]

    if weather.wind_gust is not None:
        lines.append(f"🌬 Порывы до: {fmt_float(weather.wind_gust, ' м/с')}")

    lines.append(f"📊 Давление: {weather.pressure} гПа")
    lines.append(f"☁️ Облачность: {weather.clouds}%")

    if weather.rain_1h is not None:
        lines.append(f"🌧 Осадки (дождь): {fmt_float(weather.rain_1h, ' мм')}")
    if weather.snow_1h is not None:
        lines.append(f"❄️ Осадки (снег): {fmt_float(weather.snow_1h, ' мм')}")

    if weather.visibility and weather.visibility < 10000:
        lines.append(f"🌫 Видимость: {fmt_float(weather.visibility / 1000, ' км')}")

    lines.append(f"📝 {weather.description.capitalize()}")

    g_url = gismeteo_url(weather.city_name)
    if g_url:
        lines.append(f"\n🌐 <a href='{g_url}'>Gismeteo</a>")

    return "\n".join(lines)
