#!/usr/bin/env bash
# Install git hooks for the Osmosis project.
# Run once after cloning: bash scripts/setup-hooks.sh
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

HOOK_DIR=".git/hooks"

# Pre-commit hook
cat > "$HOOK_DIR/pre-commit" << 'HOOK'
#!/usr/bin/env bash
set -euo pipefail
echo "Running pre-commit quality checks..."
echo ""
exec bash "$(git rev-parse --show-toplevel)/scripts/code-quality-check.sh"
HOOK
chmod +x "$HOOK_DIR/pre-commit"

# Commit-msg hook — enforce conventional commit format
cat > "$HOOK_DIR/commit-msg" << 'HOOK'
#!/usr/bin/env bash
# Enforce conventional commit messages.
# Format: type(optional-scope): description
# Types: feat, fix, refactor, docs, test, chore, ci, style, perf, build
set -euo pipefail

MSG_FILE="$1"
MSG=$(head -1 "$MSG_FILE")

# Allow merge commits and reverts
if echo "$MSG" | grep -qE '^(Merge|Revert) '; then
    exit 0
fi

PATTERN='^(feat|fix|refactor|docs|test|chore|ci|style|perf|build)(\([a-z0-9_-]+\))?: .{3,}'

if ! echo "$MSG" | grep -qE "$PATTERN"; then
    echo ""
    echo "COMMIT MESSAGE REJECTED"
    echo ""
    echo "  Must follow conventional commits format:"
    echo "    type(scope): description"
    echo ""
    echo "  Types: feat, fix, refactor, docs, test, chore, ci, style, perf, build"
    echo "  Example: feat(flash): add auto-detection for Download Mode"
    echo "  Example: fix(sideload): handle stalled transfers at low percentage"
    echo ""
    echo "  Your message: $MSG"
    echo ""
    exit 1
fi
HOOK
chmod +x "$HOOK_DIR/commit-msg"

echo "Installed: pre-commit hook"
echo "Installed: commit-msg hook (conventional commits)"
echo ""
echo "Hooks are active. Run 'git commit --no-verify' to bypass (WIP only)."
