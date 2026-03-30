#!/usr/bin/env bash
# Unified code-quality script — run by pre-commit and CI.
# Usage: scripts/code-quality-check.sh [--fix]
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# Activate venv if present (so ruff/pytest are found)
if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

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

# ── 2. Profile hash check ─────────────────────────────────────────
echo "=== Profile hash check ==="
if ! bash scripts/check-profile-hashes.sh; then
    FAILED=1
fi
echo ""

# ── 3. Python linting (ruff) ────────────────────────────────────────
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

# ── 4. Python tests (pytest) ────────────────────────────────────────
echo "=== Tests (pytest) ==="
if command -v pytest &>/dev/null; then
    pytest tests/ -q --tb=short || FAILED=1
elif python3 -m pytest --version &>/dev/null 2>&1; then
    python3 -m pytest tests/ -q --tb=short || FAILED=1
else
    echo "SKIP: pytest not installed (pip install pytest)"
fi
echo ""

# ── 5. Secret scanning ────────────────────────────────────────────────
echo "=== Secret scanning ==="
if command -v gitleaks &>/dev/null; then
    gitleaks detect --source . --no-git -q || FAILED=1
else
    # Lightweight fallback: grep staged files for common secret patterns
    SECRETS_FOUND=0
    while IFS= read -r file; do
        [ -f "$file" ] || continue
        case "$file" in
            .venv/*|node_modules/*|*.pyc|*.bin|*.img) continue ;;
        esac
        if grep -PnH '(?i)(api[_-]?key|api[_-]?secret|password|secret[_-]?key|access[_-]?token)\s*[:=]\s*["\x27][A-Za-z0-9+/=_\-]{8,}' "$file" 2>/dev/null; then
            echo "  WARN: possible secret in $file"
            SECRETS_FOUND=1
        fi
    done < <(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || git ls-files)
    if [ "$SECRETS_FOUND" -eq 1 ]; then
        echo "Potential secrets detected. Review the lines above."
        FAILED=1
    else
        echo "OK: No obvious secrets found. (Install gitleaks for deeper scanning)"
    fi
fi
echo ""

# ── 6. Frontend lint (eslint + vue) ───────────────────────────────────
echo "=== Frontend lint (eslint) ==="
if [ -f frontend/node_modules/.bin/eslint ]; then
    if [ -n "$FIX_FLAG" ]; then
        (cd frontend && npx eslint --fix 'src/**/*.{js,vue}') || FAILED=1
    else
        # --max-warnings 0 would fail on warnings; omit to fail only on errors
        (cd frontend && npx eslint --quiet 'src/**/*.{js,vue}') || FAILED=1
    fi
else
    echo "SKIP: frontend eslint not installed (cd frontend && npm install)"
fi
echo ""

# ── 7. Shell script lint (shellcheck, optional) ─────────────────────
echo "=== Shell lint (shellcheck) ==="
if command -v shellcheck &>/dev/null; then
    shellcheck scripts/*.sh || FAILED=1
else
    echo "SKIP: shellcheck not installed"
fi
echo ""

# ── 8. Dependency audit (optional, non-blocking) ─────────────────────
echo "=== Dependency audit ==="
AUDIT_ISSUES=0
if [ -f frontend/package-lock.json ] && command -v npm &>/dev/null; then
    echo "  npm audit..."
    (cd frontend && npm audit --omit=dev 2>&1) || AUDIT_ISSUES=1
fi
if command -v pip-audit &>/dev/null; then
    echo "  pip-audit..."
    pip-audit -r requirements.txt 2>/dev/null || pip-audit 2>/dev/null || AUDIT_ISSUES=1
fi
if [ "$AUDIT_ISSUES" -eq 1 ]; then
    echo "WARN: Dependency vulnerabilities found. Review above. (non-blocking)"
else
    echo "OK (or audit tools not installed — pip install pip-audit)"
fi
echo ""

# ── Result ──────────────────────────────────────────────────────────
if [ "$FAILED" -eq 1 ]; then
    echo "QUALITY CHECK FAILED — fix the issues above before committing."
    exit 1
fi

echo "All quality checks passed."
