#!/usr/bin/env bash
# Ensure Node 20+ is available. If nvm is installed and Node is too old,
# auto-switch. Otherwise, print clear instructions and exit.
set -euo pipefail

MIN_NODE=20

# Source nvm if available but not loaded
if ! command -v nvm &>/dev/null && [ -s "$HOME/.nvm/nvm.sh" ]; then
  . "$HOME/.nvm/nvm.sh"
fi

# If nvm is loaded and .nvmrc exists, let nvm handle it
if command -v nvm &>/dev/null && [ -f "frontend/.nvmrc" ]; then
  nvm use --silent 2>/dev/null || nvm install --silent
fi

NODE_MAJOR=$(node --version 2>/dev/null | sed 's/v\([0-9]*\).*/\1/' || echo "0")

if [ "$NODE_MAJOR" -eq 0 ]; then
  echo "ERROR: Node.js not found."
  echo ""
  echo "  Install Node 20+ with nvm (recommended):"
  echo "    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash"
  echo "    nvm install 20"
  echo ""
  echo "  Or install directly:"
  echo "    https://nodejs.org/en/download"
  exit 1
fi

if [ "$NODE_MAJOR" -lt "$MIN_NODE" ]; then
  if command -v nvm &>/dev/null; then
    echo "Node $NODE_MAJOR detected — installing Node $MIN_NODE via nvm..."
    nvm install "$MIN_NODE"
    nvm use "$MIN_NODE"
  else
    echo "ERROR: Node $NODE_MAJOR detected — OSmosis requires Node $MIN_NODE+."
    echo ""
    echo "  Upgrade with nvm:"
    echo "    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash"
    echo "    nvm install $MIN_NODE"
    echo ""
    echo "  Or update your system Node:"
    echo "    https://nodejs.org/en/download"
    exit 1
  fi
fi
