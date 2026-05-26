"""Tests for auto_punch.notify."""
from __future__ import annotations

from unittest.mock import patch

from auto_punch.notify import notify


def test_notify_calls_osascript_with_message_and_title():
    with patch("auto_punch.notify.subprocess.run") as run:
        notify("auto-punch", "hello")
    args = run.call_args[0][0]
    assert args[0] == "osascript"
    assert "-e" in args
    script = args[args.index("-e") + 1]
    assert "display notification" in script
    assert "hello" in script
    assert "auto-punch" in script


def test_notify_escapes_double_quotes():
    with patch("auto_punch.notify.subprocess.run") as run:
        notify("auto-punch", 'has "quotes"')
    script = run.call_args[0][0][2]
    assert '\\"quotes\\"' in script


def test_notify_error_level_adds_sound():
    with patch("auto_punch.notify.subprocess.run") as run:
        notify("t", "m", level="error")
    script = run.call_args[0][0][2]
    assert "sound name" in script
