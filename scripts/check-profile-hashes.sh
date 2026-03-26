#!/usr/bin/env bash
# Check that device profile firmware entries with a download URL also have a sha256.
# Entries without a url (e.g. stock pages, app stores) are exempt.
# Exit 0 = all good, exit 1 = missing hashes found.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

PROFILES_DIR="profiles"
FAILED=0

# Only check staged profile files if called from pre-commit context,
# otherwise check all profiles.
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    STAGED=$(git diff --cached --name-only --diff-filter=ACM -- "$PROFILES_DIR/*.yaml" "$PROFILES_DIR/*.yml" 2>/dev/null || true)
else
    STAGED=""
fi

if [ -n "$STAGED" ]; then
    FILES="$STAGED"
else
    FILES=$(find "$PROFILES_DIR" -name '*.yaml' -o -name '*.yml' 2>/dev/null || true)
fi

if [ -z "$FILES" ]; then
    echo "No profile files to check."
    exit 0
fi

for file in $FILES; do
    [ -f "$file" ] || continue

    # Parse firmware entries: find lines with "- id:" to start a block,
    # then look for url and sha256 within that block.
    in_firmware=0
    current_id=""
    has_url=0
    has_sha256=0
    lineno=0

    while IFS= read -r line; do
        lineno=$((lineno + 1))

        # Detect firmware: section
        if echo "$line" | grep -qE '^firmware:'; then
            in_firmware=1
            continue
        fi

        # Exit firmware section on a non-indented, non-empty line
        if [ "$in_firmware" -eq 1 ] && echo "$line" | grep -qE '^[a-z_]'; then
            # Flush last entry
            if [ -n "$current_id" ] && [ "$has_url" -eq 1 ] && [ "$has_sha256" -eq 0 ]; then
                echo "  MISSING sha256: $file -> firmware '$current_id' has a url but no sha256"
                FAILED=1
            fi
            in_firmware=0
            current_id=""
            has_url=0
            has_sha256=0
            continue
        fi

        [ "$in_firmware" -eq 0 ] && continue

        # New firmware entry
        if echo "$line" | grep -qE '^\s+- id:\s'; then
            # Flush previous entry
            if [ -n "$current_id" ] && [ "$has_url" -eq 1 ] && [ "$has_sha256" -eq 0 ]; then
                echo "  MISSING sha256: $file -> firmware '$current_id' has a url but no sha256"
                FAILED=1
            fi
            current_id=$(echo "$line" | sed 's/.*- id:\s*//')
            has_url=0
            has_sha256=0
            continue
        fi

        # Check for url (non-empty)
        if echo "$line" | grep -qE '^\s+url:\s+\S'; then
            has_url=1
        fi

        # Check for sha256 (non-empty)
        if echo "$line" | grep -qE '^\s+sha256:\s+\S'; then
            has_sha256=1
        fi

    done < "$file"

    # Flush last entry in file
    if [ -n "$current_id" ] && [ "$has_url" -eq 1 ] && [ "$has_sha256" -eq 0 ]; then
        echo "  MISSING sha256: $file -> firmware '$current_id' has a url but no sha256"
        FAILED=1
    fi
done

if [ "$FAILED" -eq 1 ]; then
    echo ""
    echo "Some firmware entries have a download URL but no sha256 hash."
    echo "Add the upstream checksum, or set 'sha256: \"\"' to explicitly mark it unknown."
    exit 1
fi

echo "All firmware entries with URLs have sha256 hashes."
exit 0
