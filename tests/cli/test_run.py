"""Tests for auto_punch.cli.run."""
from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time


TAIPEI = ZoneInfo("Asia/Taipei")


@pytest.fixture
def configured_env(env_path):
    env_path.write_text(
        "APOLLO_COMPANY_CODE=acme\n"
        "APOLLO_USERNAME=alice\n"
        "APOLLO_PASSWORD=pw\n"
        "APOLLO_COOKIES=cookie_blob\n"
        "AUTO_PUNCH_SECRET=s\n"
        f"AUTO_PUNCH_LOG={env_path.parent / 'auto_punch.log'}\n"
    )
    return env_path


def _args(ptype="in", dry_run=False):
    return SimpleNamespace(type=ptype, dry_run=dry_run)


@freeze_time("2026-05-30 08:30:00+08:00")  # Saturday, Taipei time
def test_run_skips_weekend(configured_env):
    from auto_punch.cli.run import run_command
    rc = run_command(_args())
    assert rc == 0
    log_path = configured_env.parent / "auto_punch.log"
    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert entries[-1]["reason"] == "weekend"


@freeze_time("2026-01-01 08:30:00+08:00")  # New Year's Day TW holiday (Thursday), Taipei time
def test_run_skips_holiday(configured_env):
    from auto_punch.cli.run import run_command
    rc = run_command(_args())
    assert rc == 0
    log_path = configured_env.parent / "auto_punch.log"
    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert entries[-1]["reason"] == "holiday"


@freeze_time("2026-05-26 08:30:00+08:00")  # Tuesday, no holiday, Taipei time
def test_run_skips_when_already_punched(configured_env):
    from auto_punch.cli.run import run_command
    rec = {"AttendanceDate": "2026-05-26T00:00:00", "InAttendanceOn": "2026-05-26T09:00:00+08:00"}
    with patch("auto_punch.cli.run.fetch_today_record", return_value=rec):
        rc = run_command(_args())
    assert rc == 0
    log_path = configured_env.parent / "auto_punch.log"
    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert entries[-1]["reason"] == "already_punched"


@freeze_time("2026-05-26 08:30:00+08:00")  # Taipei time
def test_run_skips_when_on_leave(configured_env):
    from auto_punch.cli.run import run_command
    rec = {"AttendanceDate": "2026-05-26T00:00:00", "InTimeoutTypeText": "特休"}
    with patch("auto_punch.cli.run.fetch_today_record", return_value=rec):
        rc = run_command(_args())
    assert rc == 0
    log_path = configured_env.parent / "auto_punch.log"
    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert entries[-1]["reason"] == "leave"


@freeze_time("2026-05-26 08:30:00+08:00")  # Taipei time, before target
def test_run_dry_run_prints_plan(configured_env, capsys):
    from auto_punch.cli.run import run_command
    with patch("auto_punch.cli.run.fetch_today_record", return_value=None):
        rc = run_command(_args(dry_run=True))
    out = capsys.readouterr().out
    assert rc == 0
    assert "[dry-run]" in out
    assert "type=in" in out


@freeze_time("2026-05-26 09:31:00+08:00")  # Taipei time; past 09:20+10min grace (offset=15, target=09:15, grace boundary=09:25)
def test_run_too_late_exits_1_and_notifies(configured_env):
    from auto_punch.cli.run import run_command
    with patch("auto_punch.cli.run.fetch_today_record", return_value=None), \
         patch("auto_punch.cli.run.notify") as notify_mock:
        rc = run_command(_args())
    assert rc == 1
    notify_mock.assert_called()
    log_path = configured_env.parent / "auto_punch.log"
    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert entries[-1]["reason"] == "woke_up_late"
    assert entries[-1]["status"] == "error"


@freeze_time("2026-05-26 09:00:00+08:00")  # Taipei time, before target (offset=15 → target=09:15)
def test_run_happy_path_punches_and_notifies(configured_env):
    from auto_punch.cli.run import run_command
    punch_result = {"LocationName": "office", "punchDate": "2026-05-26T09:03:00+08:00"}
    with patch("auto_punch.cli.run.fetch_today_record", return_value=None), \
         patch("auto_punch.cli.run.punch_in", return_value=punch_result) as p_in, \
         patch("auto_punch.cli.run.time.sleep") as sleep_mock, \
         patch("auto_punch.cli.run.notify") as notify_mock:
        rc = run_command(_args())
    assert rc == 0
    p_in.assert_called_once()
    notify_mock.assert_called()
    args, kwargs = notify_mock.call_args
    assert "✅" in args[1] or "打卡完成" in args[1]


@freeze_time("2026-05-26 09:00:00+08:00")  # Taipei time
def test_run_refreshes_cookies_on_auth_error_then_succeeds(configured_env):
    from auto_punch.apollo.client import ApolloAuthError
    from auto_punch.cli.run import run_command

    # First fetch_today_record raises ApolloAuthError, second returns None
    fetch_mock = MagicMock(side_effect=[ApolloAuthError("expired"), None])

    with patch("auto_punch.cli.run.fetch_today_record", fetch_mock), \
         patch("auto_punch.cli.run.refresh_cookies", return_value="fresh") as refresh_mock, \
         patch("auto_punch.cli.run.punch_in", return_value={"LocationName": "office"}), \
         patch("auto_punch.cli.run.time.sleep"), \
         patch("auto_punch.cli.run.notify"):
        rc = run_command(_args())
    assert rc == 0
    refresh_mock.assert_called_once()
    assert fetch_mock.call_count == 2


@freeze_time("2026-05-26 09:00:00+08:00")  # Taipei time
def test_run_exit_1_when_refresh_also_fails(configured_env):
    from auto_punch.apollo.client import ApolloAuthError
    from auto_punch.apollo.login import LoginError
    from auto_punch.cli.run import run_command

    with patch("auto_punch.cli.run.fetch_today_record", side_effect=ApolloAuthError("expired")), \
         patch("auto_punch.cli.run.refresh_cookies", side_effect=LoginError("creds bad")), \
         patch("auto_punch.cli.run.notify") as notify_mock, \
         patch("auto_punch.cli.run.time.sleep"):
        rc = run_command(_args())
    assert rc == 1
    notify_mock.assert_called()
