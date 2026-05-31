from __future__ import annotations

import random


_TIPS: list[str] = [
    "🧥 Если сегодня ветер {wind} м/с, лучше одеться слоями — верхняя одежда спасёт от ветра, а под неё можно что-то лёгкое.",
    "☂️ Сегодня {desc}, не забудь зонт! Даже если сейчас сухо — {desc} может начаться внезапно.",
    "💧 Влажность {humidity}% — кожа будет благодарна за увлажняющий крем. И не забудь пить воду в течение дня.",
    "🌡 {temp}°C — перепад с утренней температурой может быть сильным. Одевайся так, чтобы можно было снять лишнее.",
    "👟 В такую погоду ({desc}) лучше выбрать обувь с нескользящей подошвой — безопасность превыше всего.",
    "🕶 UV-индекс {uvi} — {uv_tip}. Даже в пасмурную погоду ультрафиолет проникает через облака.",
    "💊 Если чувствуешь метеозависимость — сегодня {pressure} гПа. Может болеть голова, пей больше воды и отдыхай.",
    "🏃 {'Самое время для прогулки!' if float(temp) > 15 else 'Для активного отдыха одевайся теплее'} Сегодня {desc}, {temp}°C.",
    "🚗 Ветер {wind} м/с — будь аккуратен на дороге. Особенно на мостах и открытых участках трассы.",
    "🌙 Вечером ожидается {night_temp}°C — планируй возвращение домой заранее и одевайся по погоде.",
]


def random_tip(
    temp: float = 0,
    desc: str = "без осадков",
    wind: float = 0,
    humidity: int = 50,
    pressure: int = 1013,
    uvi: float | None = None,
    night_temp: float | None = None,
) -> str:
    tip = random.choice(_TIPS)
    uv_tip = "низкий, защита не обязательна"
    if uvi is not None:
        if uvi > 5:
            uv_tip = "высокий, нужен крем SPF 30+"
        elif uvi > 3:
            uv_tip = "умеренный, лучше нанести крем"
        else:
            uv_tip = "низкий, можно без защиты"
    else:
        uvi = "—"

    night = f"{night_temp:.0f}°C" if night_temp is not None else "прохладно"

    return tip.format(
        temp=f"{temp:.0f}" if isinstance(temp, float) else str(temp),
        desc=desc,
        wind=f"{wind:.0f}" if isinstance(wind, float) else str(wind),
        humidity=humidity,
        pressure=pressure,
        uvi=uvi,
        uv_tip=uv_tip,
        night_temp=night,
    )
