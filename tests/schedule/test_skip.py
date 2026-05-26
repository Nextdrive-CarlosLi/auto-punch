"""Tests for schedule.skip."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from auto_punch.schedule.skip import is_weekend, get_holiday_name, is_too_late


TAIPEI = ZoneInfo("Asia/Taipei")


def test_is_weekend_saturday_sunday():
    assert is_weekend(date(2026, 5, 30))   # Saturday
    assert is_weekend(date(2026, 5, 31))   # Sunday
    assert not is_weekend(date(2026, 5, 29))  # Friday


def test_get_holiday_name_returns_string_for_known_tw_holiday():
    # 2026/1/1 is New Year — should be a holiday in TW
    name = get_holiday_name(date(2026, 1, 1))
    assert name is not None
    assert isinstance(name, str)


def test_get_holiday_name_returns_none_for_normal_day():
    # A non-holiday weekday — pick one well away from any TW holiday window.
    # 2026/5/26 (Tuesday) is well past Lunar New Year, not in any common holiday window.
    assert get_holiday_name(date(2026, 5, 26)) is None


def test_is_too_late_within_grace():
    target = datetime(2026, 5, 26, 9, 0, tzinfo=TAIPEI)
    assert not is_too_late(target + timedelta(minutes=9), target, grace_min=10)


def test_is_too_late_past_grace():
    target = datetime(2026, 5, 26, 9, 0, tzinfo=TAIPEI)
    assert is_too_late(target + timedelta(minutes=11), target, grace_min=10)


def test_is_too_late_exactly_at_grace_boundary():
    target = datetime(2026, 5, 26, 9, 0, tzinfo=TAIPEI)
    # exactly target + grace = NOT too late (>, not >=)
    assert not is_too_late(target + timedelta(minutes=10), target, grace_min=10)
