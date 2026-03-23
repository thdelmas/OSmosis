#!/usr/bin/env bash
# Configure iptables firewall for an OSmosis instance.
# Opens only the ports OSmosis needs and drops everything else.
#
# Safe to run multiple times — flushes the OSmosis chain before rebuilding.
#
# Usage:
#   sudo bash scripts/setup-firewall.sh            # default (HTTPS + SSH)
#   sudo bash scripts/setup-firewall.sh --no-ssh   # skip SSH rule
#
# Ports opened:
#   22   — SSH (unless --no-ssh)
#   80   — HTTP (redirect to HTTPS via nginx)
#   443  — HTTPS (nginx reverse proxy)
#   5353 — mDNS (device discovery, optional)
set -euo pipefail

ALLOW_SSH=true
ALLOW_MDNS=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-ssh)   ALLOW_SSH=false;  shift ;;
        --no-mdns)  ALLOW_MDNS=false; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    echo "Error: This script must be run as root (sudo)."
    exit 1
fi

# Use iptables if available, otherwise try nftables
if command -v iptables &>/dev/null; then
    FW="iptables"
elif command -v nft &>/dev/null; then
    FW="nft"
else
    echo "Error: Neither iptables nor nft found. Install one first."
    exit 1
fi

echo "Using firewall backend: $FW"

if [[ "$FW" == "iptables" ]]; then
    CHAIN="OSMOSIS"

    # Create or flush the OSmosis chain
    iptables -N "$CHAIN" 2>/dev/null || iptables -F "$CHAIN"

    # Remove old jump rule if it exists, then re-add it
    iptables -D INPUT -j "$CHAIN" 2>/dev/null || true
    iptables -I INPUT 1 -j "$CHAIN"

    # --- Rules ---

    # Allow loopback (Flask <-> nginx on localhost)
    iptables -A "$CHAIN" -i lo -j ACCEPT

    # Allow established/related connections
    iptables -A "$CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

    # SSH
    if $ALLOW_SSH; then
        iptables -A "$CHAIN" -p tcp --dport 22 -j ACCEPT
        echo "  Allowed: SSH (22/tcp)"
    fi

    # HTTP + HTTPS (nginx)
    iptables -A "$CHAIN" -p tcp --dport 80 -j ACCEPT
    iptables -A "$CHAIN" -p tcp --dport 443 -j ACCEPT
    echo "  Allowed: HTTP (80/tcp), HTTPS (443/tcp)"

    # mDNS for device discovery
    if $ALLOW_MDNS; then
        iptables -A "$CHAIN" -p udp --dport 5353 -j ACCEPT
        echo "  Allowed: mDNS (5353/udp)"
    fi

    # ICMP (ping)
    iptables -A "$CHAIN" -p icmp --icmp-type echo-request -j ACCEPT

    # Drop everything else that hits this chain
    iptables -A "$CHAIN" -j DROP
    echo "  Default: DROP"

    # Save rules if possible
    if command -v iptables-save &>/dev/null; then
        if [[ -d /etc/iptables ]]; then
            iptables-save > /etc/iptables/rules.v4
            echo "Rules saved to /etc/iptables/rules.v4"
        elif command -v netfilter-persistent &>/dev/null; then
            netfilter-persistent save
            echo "Rules saved via netfilter-persistent."
        fi
    fi

else
    # nftables path
    nft add table inet osmosis 2>/dev/null || true
    nft flush table inet osmosis

    RULES="table inet osmosis {
    chain input {
        type filter hook input priority 0; policy drop;

        iif lo accept
        ct state established,related accept
        $(if $ALLOW_SSH; then echo 'tcp dport 22 accept'; fi)
        tcp dport { 80, 443 } accept
        $(if $ALLOW_MDNS; then echo 'udp dport 5353 accept'; fi)
        icmp type echo-request accept
    }
}"

    echo "$RULES" | nft -f -
    echo "nftables rules applied."

    # Persist
    if [[ -d /etc/nftables.d ]]; then
        echo "$RULES" > /etc/nftables.d/osmosis.nft
        echo "Rules saved to /etc/nftables.d/osmosis.nft"
    fi
fi

echo ""
echo "Firewall configured for OSmosis."
echo "Flask (port 5000) is NOT exposed — only accessible via nginx on localhost."
