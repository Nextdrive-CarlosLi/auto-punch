"""Tests for auto_punch.apollo.records."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from auto_punch.apollo.records import (
    fetch_today_record, is_already_punched, is_on_leave,
)


def test_fetch_today_record_returns_today_row():
    today = date(2026, 5, 26)
    client = MagicMock()
    client.get.return_value = {"Data": [
        {"AttendanceDate": "2026-05-25T00:00:00"},
        {"AttendanceDate": "2026-05-26T00:00:00", "InAttendanceOn": "2026-05-26T09:00:00+08:00"},
    ]}
    rec = fetch_today_record(client, today)
    assert rec["InAttendanceOn"] == "2026-05-26T09:00:00+08:00"


def test_fetch_today_record_returns_none_when_missing():
    today = date(2026, 5, 26)
    client = MagicMock()
    client.get.return_value = {"Data": []}
    assert fetch_today_record(client, today) is None


def test_is_already_punched_in_field():
    rec = {"InAttendanceOn": "2026-05-26T09:00:00+08:00", "OutAttendanceOn": None}
    assert is_already_punched(rec, "in") is True
    assert is_already_punched(rec, "out") is False


def test_is_on_leave_detects_keywords():
    rec = {"InTimeoutTypeText": "特休", "OutTimeoutTypeText": ""}
    assert is_on_leave(rec, "in") == "特休"
    assert is_on_leave(rec, "out") is None


def test_is_on_leave_returns_none_for_empty():
    assert is_on_leave({"InTimeoutTypeText": "", "OutTimeoutTypeText": ""}, "in") is None
