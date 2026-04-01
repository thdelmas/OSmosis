#!/usr/bin/env bash
# Install and configure IPFS (kubo) if not already present.
# Installs to ~/.local/bin (no sudo required).
# Called by `make install`. Safe to run multiple times.
set -euo pipefail

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

# Ensure ~/.local/bin is on PATH for this script
export PATH="$LOCAL_BIN:$PATH"

if command -v ipfs &>/dev/null; then
  echo "IPFS already installed: $(ipfs version)"
else
  echo "Installing IPFS (kubo) to $LOCAL_BIN..."

  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64)  GO_ARCH="amd64" ;;
    aarch64) GO_ARCH="arm64" ;;
    armv7l)  GO_ARCH="arm" ;;
    *)       GO_ARCH="amd64" ;;
  esac

  # Fetch latest stable version
  VERSION="v0.33.2"
  VERSIONS=$(curl -sL --max-time 10 "https://dist.ipfs.tech/kubo/versions" 2>/dev/null || true)
  if [ -n "$VERSIONS" ]; then
    LATEST=$(echo "$VERSIONS" | grep '^v' | grep -v '\-rc' | tail -1 | tr -d '[:space:]')
    [ -n "$LATEST" ] && VERSION="$LATEST"
  fi

  URL="https://dist.ipfs.tech/kubo/${VERSION}/kubo_${VERSION}_linux-${GO_ARCH}.tar.gz"
  TMPDIR=$(mktemp -d)
  trap 'rm -rf "$TMPDIR"' EXIT

  echo "Downloading kubo ${VERSION} for ${GO_ARCH}..."
  echo "  $URL"
  if command -v curl &>/dev/null; then
    curl -L --progress-bar -o "$TMPDIR/kubo.tar.gz" "$URL"
  elif command -v wget &>/dev/null; then
    wget --progress=bar:force -O "$TMPDIR/kubo.tar.gz" "$URL" 2>&1
  else
    echo "ERROR: Neither curl nor wget found." >&2
    exit 1
  fi

  echo "Extracting..."
  tar xzf "$TMPDIR/kubo.tar.gz" -C "$TMPDIR"

  cp "$TMPDIR/kubo/ipfs" "$LOCAL_BIN/ipfs"
  chmod +x "$LOCAL_BIN/ipfs"

  echo "IPFS installed: $($LOCAL_BIN/ipfs version)"

  # Remind about PATH if needed
  if ! command -v ipfs &>/dev/null; then
    echo ""
    echo "NOTE: Add ~/.local/bin to your PATH if not already:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  fi
fi

# Initialize repo if needed
if [ ! -d "$HOME/.ipfs" ]; then
  echo "Initializing IPFS repository (this may take a moment)..."
  ipfs init

  # Harden: API and gateway on localhost only
  echo "Securing IPFS configuration (localhost only)..."
  ipfs config Addresses.API /ip4/127.0.0.1/tcp/5001
  ipfs config Addresses.Gateway /ip4/127.0.0.1/tcp/8080
  ipfs config --json API.HTTPHeaders.Access-Control-Allow-Origin '["http://127.0.0.1:5001"]'
  ipfs config --json API.HTTPHeaders.Access-Control-Allow-Methods '["PUT", "POST", "GET"]'
  echo "IPFS API restricted to localhost."
fi

echo "IPFS setup complete."
