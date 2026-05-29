from __future__ import annotations


def celsius_to_symbol(temp: float) -> str:
    if temp > 25:
        return "🥵"
    if temp > 15:
        return "😎"
    if temp > 5:
        return "🙂"
    if temp > -5:
        return "🥶"
    return "❄️"


def wind_description(speed: float) -> str:
    if speed < 1:
        return "штиль"
    if speed < 5:
        return "лёгкий"
    if speed < 10:
        return "умеренный"
    if speed < 15:
        return "сильный"
    return "штормовой"


def fmt_float(value: float | None, unit: str = "", digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}{unit}"
