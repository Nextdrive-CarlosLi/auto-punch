"""Tests for schedule.offset."""
from __future__ import annotations

from datetime import date

from auto_punch.schedule.offset import compute_offset


def test_offset_is_deterministic():
    d = date(2026, 5, 26)
    assert compute_offset(d, "secret1") == compute_offset(d, "secret1")


def test_offset_changes_with_secret():
    d = date(2026, 5, 26)
    a = compute_offset(d, "secret1")
    b = compute_offset(d, "secret2")
    assert a != b


def test_offset_changes_across_days():
    out = {compute_offset(date(2026, 1, i), "s") for i in range(1, 32)}
    assert len(out) > 1


def test_offset_in_range():
    for i in range(1, 32):
        x = compute_offset(date(2026, 1, i), "s")
        assert -10 <= x <= 20
