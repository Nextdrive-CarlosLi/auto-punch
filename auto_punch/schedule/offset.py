"""Deterministic per-day offset for auto-punch.

Same (date, secret) → same offset. Range: -10 to +20 inclusive (31 values).
"""
from __future__ import annotations

import hashlib
from datetime import date


def compute_offset(today: date, secret: str) -> int:
    """Return offset in minutes ∈ [-10, +20]."""
    payload = f"{today.isoformat()}|{secret}".encode()
    digest = hashlib.sha256(payload).digest()
    bucket = int.from_bytes(digest[:4], "big") % 31
    return bucket - 10
