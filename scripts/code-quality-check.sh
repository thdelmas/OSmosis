#!/usr/bin/env bash
# Unified code-quality script — run by pre-commit and CI.
# Usage: scripts/code-quality-check.sh [--fix]
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

FIX_FLAG=""
if [ "${1:-}" = "--fix" ]; then
    FIX_FLAG="--fix"
fi

FAILED=0

# ── 1. File-length check ────────────────────────────────────────────
echo "=== File-length check ==="
if ! bash scripts/check-file-length.sh; then
    FAILED=1
fi
echo ""

# ── 2. Python linting (ruff) ────────────────────────────────────────
echo "=== Python lint (ruff) ==="
if command -v ruff &>/dev/null; then
    if [ -n "$FIX_FLAG" ]; then
        ruff check --fix . || FAILED=1
        ruff format . || FAILED=1
    else
        ruff check . || FAILED=1
        ruff format --check . || FAILED=1
    fi
else
    echo "SKIP: ruff not installed (pip install ruff)"
fi
echo ""

# ── 3. Python tests (pytest) ────────────────────────────────────────
echo "=== Tests (pytest) ==="
if command -v pytest &>/dev/null; then
    pytest tests/ -q --tb=short || FAILED=1
elif python3 -m pytest --version &>/dev/null 2>&1; then
    python3 -m pytest tests/ -q --tb=short || FAILED=1
else
    echo "SKIP: pytest not installed (pip install pytest)"
fi
echo ""

# ── 4. Shell script lint (shellcheck, optional) ─────────────────────
echo "=== Shell lint (shellcheck) ==="
if command -v shellcheck &>/dev/null; then
    shellcheck scripts/*.sh || FAILED=1
else
    echo "SKIP: shellcheck not installed"
fi
echo ""

# ── Result ───────────────────────────────────────────────────────────
if [ "$FAILED" -eq 1 ]; then
    echo "QUALITY CHECK FAILED — fix the issues above before committing."
    exit 1
fi

echo "All quality checks passed."
