#!/usr/bin/env bash
# Install git hooks for the OSmosis project.
# Run once after cloning: bash scripts/setup-hooks.sh
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# Use version-controlled hooks directory
git config core.hooksPath .githooks

# Ensure hooks are executable
chmod +x .githooks/*

echo "Configured core.hooksPath = .githooks"
echo ""
echo "Installed hooks:"
echo "  pre-commit  — code quality checks"
echo "  commit-msg  — Conventional Commits enforcement"
echo ""
echo "Hooks are active. Run 'git commit --no-verify' to bypass (WIP only)."
