#!/usr/bin/env bash
# Check that no tracked source file exceeds the line limit.
# Usage: scripts/check-file-length.sh [MAX_LINES]
set -euo pipefail

MAX_LINES="${1:-500}"
FAILED=0

# Only check tracked files; exclude vendored/generated/binary patterns
while IFS= read -r file; do
    # Skip non-text, vendored, generated, and large-by-nature patterns
    case "$file" in
        *.min.js|*.min.css|*.lock|*.sum|*/package-lock.json|package-lock.json|yarn.lock) continue ;;
        .venv/*|node_modules/*|vendor/*|__pycache__/*) continue ;;
        *.img|*.bin|*.zip|*.tar*|*.pit|*.pyc) continue ;;
        frontend/src/i18n/*.json) continue ;;  # generated locale files
        frontend/src/style.css) continue ;;   # migrated legacy CSS
        web/static/app.js|web/static/i18n.js|web/static/style.css) continue ;;  # legacy frontend (Vue migration in progress)
        web/templates/index.html) continue ;;  # legacy template
        web/scooter_proto.py|web/cfw_builder.py|web/os_builder.py) continue ;;  # protocol/build implementations
        web/routes/romfinder.py) continue ;;  # ROM finder with multi-source search logic
        osmosis.sh) continue ;;  # CLI entry point
    esac

    # Only check source-like files
    case "$file" in
        *.py|*.js|*.ts|*.html|*.css|*.sh|*.yml|*.yaml|*.json|*.cfg|*.toml) ;;
        *) continue ;;
    esac

    lines=$(wc -l < "$file" 2>/dev/null || echo 0)
    if [ "$lines" -gt "$MAX_LINES" ]; then
        echo "FAIL: $file has $lines lines (limit: $MAX_LINES)"
        FAILED=1
    fi
done < <(git ls-files 2>/dev/null)

if [ "$FAILED" -eq 1 ]; then
    echo ""
    echo "Files above exceed the $MAX_LINES-line limit."
    echo "Split them into smaller modules before committing."
    exit 1
fi

echo "OK: All source files are under $MAX_LINES lines."
