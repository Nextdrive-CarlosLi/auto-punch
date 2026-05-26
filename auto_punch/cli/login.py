"""auto-punch login sub-command."""
from __future__ import annotations

import getpass
import secrets
import sys

from auto_punch.apollo.login import LoginError, refresh_cookies
from auto_punch.config import DEFAULT_CONFIG_PATH, config_path, write_config


def login_command(args) -> int:
    path = config_path()
    if path.exists() and not args.force:
        print(f"{path} already configured. Use --force to reset.")
        return 0

    print(f"Setting up auto-punch config at {path}")
    company = input("Company code: ").strip()
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    if not (company and username and password):
        print("❌ All three fields are required.", file=sys.stderr)
        return 1

    write_config({
        "APOLLO_COMPANY_CODE": company,
        "APOLLO_USERNAME": username,
        "APOLLO_PASSWORD": password,
        "AUTO_PUNCH_SECRET": secrets.token_hex(16),
        "AUTO_PUNCH_LOG": str(DEFAULT_CONFIG_PATH.parent / "auto_punch.log"),
        "APOLLO_COOKIES": "",  # placeholder so load_config doesn't complain mid-refresh
    })

    print("Running OAuth login + BPM handshake...")
    try:
        refresh_cookies()
    except LoginError as exc:
        print(f"❌ Login failed: {exc}", file=sys.stderr)
        return 1

    print(f"✅ Logged in as {username}. CLI ready.")
    print(f"   Next: auto-punch run --type in --dry-run")
    return 0
