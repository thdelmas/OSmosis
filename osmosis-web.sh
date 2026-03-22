#!/usr/bin/env bash
#
# osmosis-web.sh — Launcher for Osmosis Web UI.
# Delegates to the Makefile. Use `make help` for all targets.
#
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ ! -d .venv ]]; then
  echo "First run — installing dependencies..."
  make install
fi

exec make serve
