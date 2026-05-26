"""Tests for auto_punch.cli.login."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest


def test_login_already_configured_without_force(env_path, capsys):
    from auto_punch.cli.login import login_command
    env_path.write_text(
        "APOLLO_COMPANY_CODE=acme\n"
        "APOLLO_USERNAME=alice\n"
        "APOLLO_PASSWORD=pw\n"
        "APOLLO_COOKIES=stale\n"
        "AUTO_PUNCH_SECRET=s\n"
        "AUTO_PUNCH_LOG=/tmp/log.jsonl\n"
    )
    rc = login_command(SimpleNamespace(force=False))
    assert rc == 0
    assert "already configured" in capsys.readouterr().out.lower()


def test_login_writes_config_and_calls_refresh(env_path, monkeypatch):
    from auto_punch.cli.login import login_command
    monkeypatch.setattr("builtins.input", lambda prompt="": {
        "Company code: ": "acme",
        "Username: ": "alice",
    }[prompt])
    monkeypatch.setattr("auto_punch.cli.login.getpass.getpass", lambda prompt="": "pw")
    with patch("auto_punch.cli.login.refresh_cookies", return_value="fresh_cookies") as r:
        rc = login_command(SimpleNamespace(force=False))
    assert rc == 0
    r.assert_called_once()
    text = env_path.read_text()
    assert "APOLLO_COMPANY_CODE=acme" in text
    assert "APOLLO_USERNAME=alice" in text
    assert "APOLLO_PASSWORD=pw" in text
    assert "AUTO_PUNCH_SECRET=" in text
    assert "AUTO_PUNCH_LOG=" in text


def test_login_force_reruns(env_path, monkeypatch):
    from auto_punch.cli.login import login_command
    env_path.write_text(
        "APOLLO_COMPANY_CODE=old\n"
        "APOLLO_USERNAME=old\n"
        "APOLLO_PASSWORD=old\n"
        "APOLLO_COOKIES=stale\n"
        "AUTO_PUNCH_SECRET=s\n"
        "AUTO_PUNCH_LOG=/tmp/x.log\n"
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": "new")
    monkeypatch.setattr("auto_punch.cli.login.getpass.getpass", lambda prompt="": "newpw")
    with patch("auto_punch.cli.login.refresh_cookies", return_value="fresh"):
        rc = login_command(SimpleNamespace(force=True))
    assert rc == 0
    text = env_path.read_text()
    assert "APOLLO_COMPANY_CODE=new" in text


def test_login_returns_1_on_login_error(env_path, monkeypatch):
    from auto_punch.apollo.login import LoginError
    from auto_punch.cli.login import login_command
    monkeypatch.setattr("builtins.input", lambda prompt="": "acme")
    monkeypatch.setattr("auto_punch.cli.login.getpass.getpass", lambda prompt="": "pw")
    with patch("auto_punch.cli.login.refresh_cookies", side_effect=LoginError("creds bad")):
        rc = login_command(SimpleNamespace(force=False))
    assert rc == 1
