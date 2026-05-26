"""Shared pytest fixtures."""
from __future__ import annotations

import pytest


@pytest.fixture
def env_path(tmp_path, monkeypatch):
    """Yield a tmp .env path and set AUTO_PUNCH_CONFIG to point at it."""
    p = tmp_path / ".env"
    monkeypatch.setenv("AUTO_PUNCH_CONFIG", str(p))
    return p
