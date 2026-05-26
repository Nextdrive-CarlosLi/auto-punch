"""Skip-decision helpers: weekend / TW holiday / late-wake."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import holidays


_TW_HOLIDAYS = holidays.country_holidays("TW")


def is_weekend(today: date) -> bool:
    """Saturday (5) or Sunday (6)."""
    return today.weekday() >= 5


def get_holiday_name(today: date) -> str | None:
    """Return TW public-holiday name if today is one, else None."""
    name = _TW_HOLIDAYS.get(today)
    return name


def is_too_late(now: datetime, target: datetime, *, grace_min: int) -> bool:
    """True if `now` is past `target + grace_min` minutes."""
    return now > target + timedelta(minutes=grace_min)
