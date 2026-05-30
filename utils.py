from __future__ import annotations


def celsius_to_symbol(t: float) -> str:
    if t > 25:
        return "☀️"
    if t > 15:
        return "⛅"
    if t > 0:
        return "☁️"
    return "❄️"


def fmt_float(value: float, suffix: str = "") -> str:
    return f"{value:.1f}{suffix}"


def wind_description(speed: float) -> str:
    if speed < 1:
        return "штиль"
    if speed < 4:
        return "лёгкий"
    if speed < 8:
        return "умеренный"
    if speed < 12:
        return "сильный"
    return "штормовой"
