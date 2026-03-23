#!/usr/bin/env bash
# Install and configure fail2ban to protect the OSmosis web UI.
# Creates a jail that watches the nginx access log for suspicious patterns
# (rapid API hits, scanner probes, auth failures).
#
# Safe to run multiple times (idempotent).
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Error: This script must be run as root (sudo)."
    exit 1
fi

# --- Install fail2ban if missing ---
if ! command -v fail2ban-client &>/dev/null; then
    echo "Installing fail2ban..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq fail2ban
    elif command -v dnf &>/dev/null; then
        dnf install -y fail2ban
    elif command -v pacman &>/dev/null; then
        pacman -S --noconfirm fail2ban
    else
        echo "Error: Could not detect package manager. Install fail2ban manually."
        exit 1
    fi
fi

# --- Create fail2ban filter for OSmosis ---
FILTER_DIR="/etc/fail2ban/filter.d"
JAIL_DIR="/etc/fail2ban/jail.d"

echo "Writing fail2ban filter..."
cat > "$FILTER_DIR/osmosis.conf" <<'FILTEREOF'
# fail2ban filter for OSmosis nginx proxy
# Matches rapid API abuse, scanner probes, and auth failures.

[Definition]

# Catch 401/403 responses (auth failures)
failregex = ^<HOST> - .* "(GET|POST|PUT|DELETE) /api/.*" (401|403)
            ^<HOST> - .* "(GET|POST|PUT|DELETE) /.*" 444

# Catch common scanner probes
            ^<HOST> - .* "(GET|POST) /(\.env|wp-admin|phpmyadmin|\.git|cgi-bin).*"
            ^<HOST> - .* "(GET|POST) /.*\.(php|asp|aspx|jsp|cgi).*"

ignoreregex =
FILTEREOF

echo "Writing fail2ban jail..."
cat > "$JAIL_DIR/osmosis.conf" <<'JAILEOF'
# OSmosis jail — protects the web UI behind nginx.
#
# Bans IPs that trigger too many 401/403 responses or scanner patterns.
# Runs alongside the default sshd jail.

[osmosis]
enabled  = true
port     = http,https
filter   = osmosis
logpath  = /var/log/nginx/access.log
maxretry = 10
findtime = 300
bantime  = 3600
action   = iptables-multiport[name=osmosis, port="http,https", protocol=tcp]
JAILEOF

# --- Enable and restart ---
systemctl enable fail2ban
systemctl restart fail2ban

echo ""
echo "fail2ban configured for OSmosis."
echo "  Filter: $FILTER_DIR/osmosis.conf"
echo "  Jail:   $JAIL_DIR/osmosis.conf"
echo ""
echo "Check status:  sudo fail2ban-client status osmosis"
echo "Unban an IP:   sudo fail2ban-client set osmosis unbanip <IP>"
