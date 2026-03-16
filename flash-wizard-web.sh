#!/usr/bin/env bash
#
# flash-wizard-web.sh
# Launcher for FlashWizard Web UI (Flask).
# Opens http://localhost:5000 in the default browser.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "========================================"
echo "  FlashWizard Web UI"
echo "========================================"
echo

# Check Python 3
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  echo "Install with:  sudo apt install python3 python3-venv"
  exit 1
fi

# Create venv if needed
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

# Activate and install deps
source "$VENV_DIR/bin/activate"

if ! python3 -c "import flask" 2>/dev/null; then
  echo "Installing dependencies..."
  pip install -q -r "$SCRIPT_DIR/requirements.txt"
fi

echo "Starting FlashWizard Web UI on http://localhost:5000"
echo "Press Ctrl+C to stop."
echo

exec python3 "$SCRIPT_DIR/web/app.py"
