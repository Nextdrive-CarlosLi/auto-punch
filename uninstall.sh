#!/usr/bin/env bash
#
# auto-punch uninstaller
#
#   curl -fsSL https://raw.githubusercontent.com/Nextdrive-CarlosLi/auto-punch/main/uninstall.sh | bash
#
# Removes:
#   - launchd plists (morning + evening)
#   - the pipx-installed package
#   - ~/.config/auto-punch/ (credentials, cookies, log) — full nuke
#
set -euo pipefail

CONFIG_DIR="$HOME/.config/auto-punch"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LABELS=(com.carlos.auto-punch.morning com.carlos.auto-punch.evening)

_step() { printf "\033[1;34m==>\033[0m %s\n" "$*"; }
_ok()   { printf "\033[1;32m✓\033[0m  %s\n" "$*"; }
_warn() { printf "\033[1;33m⚠\033[0m  %s\n" "$*"; }
_err()  { printf "\033[1;31m✗\033[0m  %s\n" "$*" >&2; }
_die()  { _err "$@"; exit 1; }

_on_exit() {
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        _err "uninstall aborted (exit $rc)"
    fi
}
trap _on_exit EXIT

# --- 1. OS check ---
[ "$(uname -s)" = "Darwin" ] || _die "auto-punch is macOS-only; nothing to uninstall on $(uname -s)"

# --- 2. unload + remove launchd plists ---
_step "removing launchd plists"
if command -v auto-punch >/dev/null 2>&1; then
    auto-punch uninstall-launchd || _warn "auto-punch uninstall-launchd exited non-zero, falling back to manual cleanup"
fi
# Belt-and-suspenders manual cleanup in case the binary is gone or its call failed
for label in "${LABELS[@]}"; do
    plist="$LAUNCH_AGENTS_DIR/$label.plist"
    launchctl unload "$plist" 2>/dev/null || true
    if [ -f "$plist" ]; then
        rm -f "$plist"
        _ok "removed $plist"
    fi
done

# --- 3. uninstall pipx package ---
_step "removing pipx package"
if command -v pipx >/dev/null 2>&1 && pipx list 2>/dev/null | grep -q "package auto-punch "; then
    pipx uninstall auto-punch
    _ok "pipx package removed"
else
    _warn "pipx package not found, skipping"
fi

# --- 4. nuke config dir ---
_step "removing config dir"
if [ -d "$CONFIG_DIR" ]; then
    rm -rf "$CONFIG_DIR"
    _ok "removed $CONFIG_DIR"
else
    _warn "$CONFIG_DIR not present, skipping"
fi

echo
echo "👋 auto-punch fully uninstalled."
