from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.core.config import Settings


DAY_MAP = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}


def is_market_open(now: datetime, settings: Settings) -> bool:
    if settings.market_allow_after_hours:
        return True

    tz = ZoneInfo(settings.market_tz)
    local = now.astimezone(tz)

    allowed_days = {DAY_MAP[d] for d in settings.market_days_list() if d in DAY_MAP}
    if local.weekday() not in allowed_days:
        return False

    open_time = _parse_time(settings.market_open_time)
    close_time = _parse_time(settings.market_close_time)
    return open_time <= local.time() <= close_time


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))
