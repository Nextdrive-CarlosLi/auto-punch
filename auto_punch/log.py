"""JSONL append-only logger."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_TAIPEI = ZoneInfo("Asia/Taipei")


def log_event(log_path: str | Path, event: dict) -> None:
    """Append one JSON event with `ts` auto-filled."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now(_TAIPEI).isoformat(timespec="seconds"), **event}
    with log_path.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
