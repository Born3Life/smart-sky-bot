from __future__ import annotations

from datetime import datetime

from .weather_forecast import fetch_raw_forecast


def fmt_windows(city: str) -> str | None:
    """Return good/bad weather windows from 3-hour forecast."""
    forecast = fetch_raw_forecast(city)
    if not forecast:
        return None

    good_blocks: list[list[dict]] = []
    bad_blocks: list[list[dict]] = []
    cur: list[dict] = []
    cur_good = True

    for e in forecast:
        good = _is_good(e)
        if good != cur_good and cur:
            (good_blocks if cur_good else bad_blocks).append(cur)
            cur = []
            cur_good = good
        cur.append(e)
    if cur:
        (good_blocks if cur_good else bad_blocks).append(cur)

    lines = []
    for block in good_blocks:
        start = _fmt_time(block[0]["dt_txt"])
        end = _fmt_time(block[-1]["dt_txt"])
        lines.append(f"✅ Хорошая погода: {start}–{end}")
    for block in bad_blocks:
        start = _fmt_time(block[0]["dt_txt"])
        end = _fmt_time(block[-1]["dt_txt"])
        desc = block[0].get("desc", "осадки")
        lines.append(f"⚠️ {desc.capitalize()}: {start}–{end}")

    return "\n".join(lines) if lines else None


def _is_good(entry: dict) -> bool:
    rain = entry.get("rain", 0) or 0
    snow = entry.get("snow", 0) or 0
    wind = entry.get("wind", 0) or 0
    temp = entry.get("temp", 20)
    desc = (entry.get("desc") or "").lower()
    if rain > 0 or snow > 0:
        return False
    if any(k in desc for k in ("дожд", "гроз", "снег")):
        return False
    if wind > 10:
        return False
    if temp < 0 or temp > 35:
        return False
    return True


def _fmt_time(dt_str: str | None) -> str:
    if dt_str is None:
        return "—"
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%H:%M")
    except (ValueError, TypeError):
        return dt_str or "—"
