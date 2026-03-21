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

echo "Installed: pre-commit hook"
echo ""
echo "Hooks are active. Run 'git commit --no-verify' to bypass (WIP only)."
