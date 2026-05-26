"""Read/write ~/.config/auto-punch/.env (or AUTO_PUNCH_CONFIG override)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "auto-punch" / ".env"


class MissingConfigError(Exception):
    """A required key is absent or the file does not exist."""


@dataclass
class Config:
    company_code: str
    username: str
    password: str
    cookies: str
    cookies_updated_at: str
    secret: str
    log_path: Path


def config_path() -> Path:
    """Resolve config path. AUTO_PUNCH_CONFIG env wins; otherwise default."""
    override = os.environ.get("AUTO_PUNCH_CONFIG")
    return Path(override).expanduser() if override else DEFAULT_CONFIG_PATH


def parse_env(text: str) -> dict[str, str]:
    """Parse `KEY=VALUE` lines. Strips matching quotes, ignores `#` comments."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        out[key] = value
    return out


_REQUIRED = (
    "APOLLO_COMPANY_CODE",
    "APOLLO_USERNAME",
    "APOLLO_PASSWORD",
    "APOLLO_COOKIES",
    "AUTO_PUNCH_SECRET",
    "AUTO_PUNCH_LOG",
)


def load_config() -> Config:
    path = config_path()
    if not path.exists():
        raise MissingConfigError(
            f"{path} not found. Run `auto-punch login` to create it."
        )
    raw = parse_env(path.read_text(encoding="utf-8"))
    missing = [k for k in _REQUIRED if not raw.get(k)]
    if missing:
        raise MissingConfigError(
            f"Missing in {path}: {', '.join(missing)}. "
            "Run `auto-punch login --force` to recreate."
        )
    return Config(
        company_code=raw["APOLLO_COMPANY_CODE"],
        username=raw["APOLLO_USERNAME"],
        password=raw["APOLLO_PASSWORD"],
        cookies=raw["APOLLO_COOKIES"],
        cookies_updated_at=raw.get("APOLLO_COOKIES_UPDATED_AT", ""),
        secret=raw["AUTO_PUNCH_SECRET"],
        log_path=Path(raw["AUTO_PUNCH_LOG"]).expanduser(),
    )


def write_config(updates: dict[str, str]) -> None:
    """Merge `updates` into config file, creating it if absent. Preserves
    existing key order and any unrelated keys."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = parse_env(path.read_text(encoding="utf-8")) if path.exists() else {}
    existing.update(updates)
    lines = [f"{k}={v}" for k, v in existing.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
