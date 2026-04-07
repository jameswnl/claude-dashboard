#!/bin/bash
# Install Claude Dashboard menubar app to /Applications
#
# Usage:
#   ./scripts/install_menubar_app.sh
#
# Prerequisites:
#   - macOS
#   - Python 3.10+ (with pip or uv)
#
# What this does:
#   1. Installs claude-dashboard with menubar support
#   2. Creates a macOS .app bundle that launches the menubar app
#   3. Copies it to /Applications/Claude Dashboard.app

set -e

APP_NAME="Claude Dashboard"
APP_DIR="/Applications/${APP_NAME}.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# --- Helpers ---

info()  { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
error() { printf '\033[1;31mError:\033[0m %s\n' "$1" >&2; exit 1; }

# --- Checks ---

[[ "$(uname)" == "Darwin" ]] || error "This script only works on macOS."

# --- Install the package ---

info "Installing claude-dashboard with menubar support..."

if command -v uv &>/dev/null; then
    cd "$PROJECT_DIR"
    uv sync --extra menubar
    PYTHON="$(uv run python -c 'import sys; print(sys.executable)')"
elif command -v pip &>/dev/null; then
    pip install -e "${PROJECT_DIR}[menubar]"
    PYTHON="$(python3 -c 'import sys; print(sys.executable)')"
else
    error "Neither uv nor pip found. Install one first."
fi

# Verify the module works
"$PYTHON" -c "import claude_dashboard.menubar" 2>/dev/null \
    || error "Failed to import claude_dashboard.menubar. Check installation."

info "Using Python: $PYTHON"

# --- Build the .app bundle ---

info "Creating ${APP_NAME}.app..."

# Clean up any previous install
if [[ -d "$APP_DIR" ]]; then
    info "Removing existing ${APP_DIR}..."
    rm -rf "$APP_DIR"
fi

# Use osacompile to create a proper macOS applet that launches the Python menubar
osacompile -o "$APP_DIR" -e "do shell script \"\\\"$PYTHON\\\" -m claude_dashboard.menubar 2>/tmp/claude-dashboard-menubar.log &\""

# Set LSUIElement so it runs as menubar-only (no Dock icon)
defaults write "${APP_DIR}/Contents/Info" LSUIElement -bool true

info "Installed to ${APP_DIR}"
echo ""
echo "  Open it from Applications or run:"
echo "    open '/Applications/${APP_NAME}.app'"
echo ""
echo "  The app runs as a menubar icon (C>_) — no Dock icon."
echo "  To start at login: System Settings > General > Login Items > add '${APP_NAME}'"
echo ""
