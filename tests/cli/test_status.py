"""Tests for auto_punch.cli.status."""
from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from freezegun import freeze_time


TAIPEI = ZoneInfo("Asia/Taipei")


def _args(days=5):
    return SimpleNamespace(days=days)


@freeze_time("2026-05-30 10:00:00+08:00")  # Saturday Taipei
def test_status_today_weekend(env_path, capsys):
    env_path.write_text(
        "APOLLO_COMPANY_CODE=a\nAPOLLO_USERNAME=u\nAPOLLO_PASSWORD=p\n"
        "APOLLO_COOKIES=c\nAUTO_PUNCH_SECRET=s\nAUTO_PUNCH_LOG=/tmp/x.log\n"
    )
    from auto_punch.cli.status import status_command
    rc = status_command(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "週末" in out or "weekend" in out.lower()


@freeze_time("2026-05-26 08:30:00+08:00")  # Tuesday Taipei
def test_status_today_scheduled(env_path, capsys):
    env_path.write_text(
        "APOLLO_COMPANY_CODE=a\nAPOLLO_USERNAME=u\nAPOLLO_PASSWORD=p\n"
        "APOLLO_COOKIES=c\nAUTO_PUNCH_SECRET=s\nAUTO_PUNCH_LOG=/tmp/x.log\n"
    )
    from auto_punch.cli.status import status_command
    with patch("auto_punch.cli.status.fetch_today_record", return_value=None):
        rc = status_command(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "IN" in out
    assert "OUT" in out
    assert "scheduled" in out or "排程" in out or "⏳" in out


@freeze_time("2026-05-26 10:00:00+08:00")  # past 09:30 boundary, Taipei
def test_status_today_missed(env_path, capsys):
    env_path.write_text(
        "APOLLO_COMPANY_CODE=a\nAPOLLO_USERNAME=u\nAPOLLO_PASSWORD=p\n"
        "APOLLO_COOKIES=c\nAUTO_PUNCH_SECRET=s\nAUTO_PUNCH_LOG=/tmp/x.log\n"
    )
    from auto_punch.cli.status import status_command
    with patch("auto_punch.cli.status.fetch_today_record", return_value=None):
        rc = status_command(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "missed" in out.lower() or "⏰" in out


@freeze_time("2026-05-26 14:00:00+08:00")
def test_status_today_already_punched_in(env_path, capsys):
    env_path.write_text(
        "APOLLO_COMPANY_CODE=a\nAPOLLO_USERNAME=u\nAPOLLO_PASSWORD=p\n"
        "APOLLO_COOKIES=c\nAUTO_PUNCH_SECRET=s\nAUTO_PUNCH_LOG=/tmp/x.log\n"
    )
    rec = {"AttendanceDate": "2026-05-26T00:00:00", "InAttendanceOn": "2026-05-26T09:03:00+08:00"}
    from auto_punch.cli.status import status_command
    with patch("auto_punch.cli.status.fetch_today_record", return_value=rec):
        rc = status_command(_args())
    out = capsys.readouterr().out
    assert "✅" in out
    assert "09:03" in out


@freeze_time("2026-05-26 08:30:00+08:00")
def test_status_shows_upcoming_weekdays(env_path, capsys):
    env_path.write_text(
        "APOLLO_COMPANY_CODE=a\nAPOLLO_USERNAME=u\nAPOLLO_PASSWORD=p\n"
        "APOLLO_COOKIES=c\nAUTO_PUNCH_SECRET=s\nAUTO_PUNCH_LOG=/tmp/x.log\n"
    )
    from auto_punch.cli.status import status_command
    with patch("auto_punch.cli.status.fetch_today_record", return_value=None):
        status_command(_args(days=3))
    out = capsys.readouterr().out
    # 2026-05-26 is Tue → next 3 weekdays: Wed 27, Thu 28, Fri 29
    assert "5/27" in out
    assert "5/28" in out
    assert "5/29" in out
