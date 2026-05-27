"""Tests for auto_punch.config."""
from __future__ import annotations

import pytest

from auto_punch.config import Config, MissingConfigError, load_config, write_config


def _write_env(path, lines):
    path.write_text("\n".join(lines) + "\n")


def test_load_config_happy_path(env_path):
    _write_env(env_path, [
        "APOLLO_COMPANY_CODE=acme",
        "APOLLO_USERNAME=alice",
        "APOLLO_PASSWORD=secret",
        "APOLLO_COOKIES=cookie_blob",
        "APOLLO_COOKIES_UPDATED_AT=2026-05-26T09:00:00+08:00",
        "AUTO_PUNCH_SECRET=abc123",
        "AUTO_PUNCH_LOG=~/log.jsonl",
    ])
    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.company_code == "acme"
    assert cfg.username == "alice"
    assert cfg.password == "secret"
    assert cfg.cookies == "cookie_blob"
    assert cfg.secret == "abc123"
    assert str(cfg.log_path).endswith("log.jsonl")


def test_load_config_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTO_PUNCH_CONFIG", str(tmp_path / "nope.env"))
    with pytest.raises(MissingConfigError, match="not found"):
        load_config()


def test_load_config_missing_key(env_path):
    _write_env(env_path, ["APOLLO_COMPANY_CODE=acme"])
    with pytest.raises(MissingConfigError, match="Missing"):
        load_config()


def test_load_config_without_cookies_is_ok(env_path):
    """APOLLO_COOKIES must not be required: on first login the file exists
    with credentials but cookies haven't been fetched yet, and run/status
    handle empty cookies by triggering refresh_cookies()."""
    _write_env(env_path, [
        "APOLLO_COMPANY_CODE=acme",
        "APOLLO_USERNAME=alice",
        "APOLLO_PASSWORD=secret",
        "AUTO_PUNCH_SECRET=s",
        "AUTO_PUNCH_LOG=/tmp/x.log",
    ])
    cfg = load_config()
    assert cfg.cookies == ""


def test_write_config_creates_file(env_path):
    write_config({"APOLLO_COMPANY_CODE": "acme", "APOLLO_USERNAME": "alice"})
    text = env_path.read_text()
    assert "APOLLO_COMPANY_CODE=acme" in text
    assert "APOLLO_USERNAME=alice" in text


def test_write_config_preserves_existing(env_path):
    _write_env(env_path, ["APOLLO_COMPANY_CODE=old", "OTHER_KEY=keep_me"])
    write_config({"APOLLO_COMPANY_CODE": "new"})
    text = env_path.read_text()
    assert "APOLLO_COMPANY_CODE=new" in text
    assert "OTHER_KEY=keep_me" in text


def test_parse_env_handles_quotes_and_comments():
    from auto_punch.config import parse_env
    text = '\n'.join([
        "# comment",
        "",
        'KEY1="quoted value"',
        "KEY2=unquoted",
        "KEY3='single quoted'",
    ])
    result = parse_env(text)
    assert result == {"KEY1": "quoted value", "KEY2": "unquoted", "KEY3": "single quoted"}
