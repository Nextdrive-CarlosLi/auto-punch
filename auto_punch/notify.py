"""macOS notification via osascript."""
from __future__ import annotations

import subprocess
from typing import Literal


def _escape(s: str) -> str:
    """Escape for AppleScript string literal: backslash and double-quote."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def notify(title: str, message: str, *, level: Literal["info", "error"] = "info") -> None:
    """Show a macOS notification. `level=error` adds a sound."""
    parts = [
        f'display notification "{_escape(message)}"',
        f'with title "{_escape(title)}"',
    ]
    if level == "error":
        parts.append('sound name "Funk"')
    script = " ".join(parts)
    subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
