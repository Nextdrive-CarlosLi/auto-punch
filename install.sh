#!/usr/bin/env bash
#
# auto-punch installer
#
#   curl -fsSL https://raw.githubusercontent.com/Nextdrive-CarlosLi/auto-punch/main/install.sh | bash
#
# What it does:
#   - macOS-only check
#   - pipx prereq (brew install, else `python3 -m pip install --user pipx`)
#   - pipx install (or upgrade if already present)
#   - smoke check the binary
#
set -euo pipefail

REPO_URL="git+https://github.com/Nextdrive-CarlosLi/auto-punch.git"

_step() { printf "\033[1;34m==>\033[0m %s\n" "$*"; }
_ok()   { printf "\033[1;32m✓\033[0m  %s\n" "$*"; }
_warn() { printf "\033[1;33m⚠\033[0m  %s\n" "$*"; }
_err()  { printf "\033[1;31m✗\033[0m  %s\n" "$*" >&2; }
_die()  { _err "$@"; exit 1; }

_on_exit() {
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        _err "install aborted (exit $rc)"
    fi
}
trap _on_exit EXIT

# --- 1. OS check ---
_step "checking platform"
if [ "$(uname -s)" != "Darwin" ]; then
    _die "auto-punch is macOS-only (uses launchd + osascript). Detected: $(uname -s)"
fi
_ok "macOS detected"

# --- 2. pipx prereq ---
if ! command -v pipx >/dev/null 2>&1; then
    _step "pipx not found, installing"
    if command -v brew >/dev/null 2>&1; then
        brew install pipx
    elif command -v python3 >/dev/null 2>&1; then
        _warn "brew not available, falling back to: python3 -m pip install --user pipx"
        python3 -m pip install --user pipx
        python3 -m pipx ensurepath
        export PATH="$HOME/.local/bin:$PATH"
        _warn "appended ~/.local/bin to PATH for this session — open a new shell to make it permanent"
    else
        _die "neither brew nor python3 available; install one and re-run"
    fi
    _ok "pipx installed"
else
    _ok "pipx found: $(command -v pipx)"
fi

# --- 3. install or upgrade ---
if pipx list 2>/dev/null | grep -q "package auto-punch "; then
    _step "auto-punch already installed, upgrading"
    pipx upgrade auto-punch
else
    _step "installing auto-punch from $REPO_URL"
    pipx install "$REPO_URL"
fi
_ok "package installed"

# --- 4. smoke check ---
_step "verifying binary"
if ! command -v auto-punch >/dev/null 2>&1; then
    _die "auto-punch not found in PATH after install. Run: pipx ensurepath && exec \$SHELL"
fi
if ! auto-punch --help >/dev/null 2>&1; then
    _die "auto-punch --help failed; install may be broken"
fi
_ok "$(command -v auto-punch)"

# --- 5. next steps ---
cat <<EOF

🎉 auto-punch installed.

Next steps:
  1. auto-punch login                       # interactive credential setup
  2. auto-punch run --type in --dry-run     # verify decision logic
  3. auto-punch install-launchd             # set up 09:00 / 18:00 cron

Docs: https://github.com/Nextdrive-CarlosLi/auto-punch
EOF
