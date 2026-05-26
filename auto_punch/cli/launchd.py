"""auto-punch install-launchd / uninstall-launchd sub-commands."""
from __future__ import annotations

import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

from auto_punch.config import MissingConfigError, load_config


LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LABELS = ("com.carlos.auto-punch.morning", "com.carlos.auto-punch.evening")


def _render_template(tmpl_name: str, cli_path: str, log_path: str) -> str:
    text = resources.files("auto_punch.launchd").joinpath(tmpl_name).read_text(encoding="utf-8")
    return text.replace("{{CLI_PATH}}", cli_path).replace("{{LOG_PATH}}", log_path)


def _smoke_test(cli_path: str) -> bool:
    """Run dry-run in + out. Both must exit 0."""
    for ptype in ("in", "out"):
        r = subprocess.run(
            [cli_path, "run", "--type", ptype, "--dry-run"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            print(f"❌ smoke test failed ({ptype}):\n{r.stderr}", file=sys.stderr)
            return False
    return True


def install_launchd_command(args) -> int:
    try:
        cfg = load_config()
    except MissingConfigError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    cli_path = shutil.which("auto-punch")
    if not cli_path:
        print("❌ `auto-punch` not found in PATH. Did pipx install succeed?", file=sys.stderr)
        return 1

    if not _smoke_test(cli_path):
        return 1

    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = str(cfg.log_path)
    for label in LABELS:
        slot = label.rsplit(".", 1)[-1]  # morning | evening
        tmpl_name = f"{label}.plist.tmpl"
        plist_text = _render_template(tmpl_name, cli_path, log_path)
        dest = LAUNCH_AGENTS_DIR / f"{label}.plist"
        # Unload first if already loaded (best-effort)
        subprocess.run(["launchctl", "unload", str(dest)], capture_output=True)
        dest.write_text(plist_text, encoding="utf-8")
        r = subprocess.run(["launchctl", "load", str(dest)], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"⚠️  launchctl load {dest.name}: {r.stderr}", file=sys.stderr)
            # Don't abort — the plist is written; user can debug

    print(f"✅ Installed plists to {LAUNCH_AGENTS_DIR}/")
    print(f"   Verify: launchctl list | grep auto-punch")
    return 0


def uninstall_launchd_command(args) -> int:
    for label in LABELS:
        dest = LAUNCH_AGENTS_DIR / f"{label}.plist"
        subprocess.run(["launchctl", "unload", str(dest)], capture_output=True)
        if dest.exists():
            dest.unlink()
    print(f"✅ Removed plists from {LAUNCH_AGENTS_DIR}/")
    return 0
