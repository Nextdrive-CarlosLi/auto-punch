"""auto-punch CLI entry point."""
from __future__ import annotations

import argparse
import sys


def run_command(args) -> int:
    from auto_punch.cli.run import run_command as impl
    return impl(args)


def status_command(args) -> int:
    from auto_punch.cli.status import status_command as impl
    return impl(args)


def login_command(args) -> int:
    from auto_punch.cli.login import login_command as impl
    return impl(args)


def install_launchd_command(args) -> int:
    from auto_punch.cli.launchd import install_launchd_command as impl
    return impl(args)


def uninstall_launchd_command(args) -> int:
    from auto_punch.cli.launchd import uninstall_launchd_command as impl
    return impl(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-punch", description="Scheduled Apollo HR auto-punch CLI")
    sub = parser.add_subparsers(dest="subcommand")

    p_login = sub.add_parser("login", help="Interactive login + cookie initialization")
    p_login.add_argument("--force", action="store_true", help="Re-prompt even if .env exists")

    p_run = sub.add_parser("run", help="Execute scheduled punch")
    p_run.add_argument("--type", choices=["in", "out"], required=True)
    p_run.add_argument("--dry-run", action="store_true")

    sub.add_parser("status", help="Show today + upcoming weekdays plan").add_argument(
        "--days", type=int, default=5,
    )

    sub.add_parser("install-launchd", help="Install macOS launchd plists")
    sub.add_parser("uninstall-launchd", help="Remove macOS launchd plists")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.subcommand is None:
        parser.print_help(sys.stderr)
        return 2
    dispatch = {
        "login": login_command,
        "run": run_command,
        "status": status_command,
        "install-launchd": install_launchd_command,
        "uninstall-launchd": uninstall_launchd_command,
    }
    return dispatch[args.subcommand](args)


if __name__ == "__main__":
    sys.exit(main())
