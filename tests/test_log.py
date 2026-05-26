"""Tests for auto_punch.log."""
from __future__ import annotations

import json

from auto_punch.log import log_event


def test_log_event_writes_jsonl(tmp_path):
    log_path = tmp_path / "x.log"
    log_event(log_path, {"type": "in", "status": "ok"})
    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["type"] == "in"
    assert entry["status"] == "ok"
    assert "ts" in entry  # auto-filled


def test_log_event_appends(tmp_path):
    log_path = tmp_path / "x.log"
    log_event(log_path, {"a": 1})
    log_event(log_path, {"a": 2})
    assert len(log_path.read_text().splitlines()) == 2


def test_log_event_creates_parent_dir(tmp_path):
    log_path = tmp_path / "nested" / "deep" / "x.log"
    log_event(log_path, {"a": 1})
    assert log_path.exists()
