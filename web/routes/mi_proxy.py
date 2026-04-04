"""Proxy and Tor configuration routes for Xiaomi Mi account API calls."""

import os
import shutil
import socket
import subprocess
import time

from flask import Blueprint, jsonify, request

bp = Blueprint("mi_proxy", __name__)


@bp.route("/api/mi-accounts/proxy", methods=["GET"])
def api_get_proxy():
    """Get the current proxy configuration for Xiaomi API calls."""
    proxy = os.environ.get("OSMOSIS_PROXY", "").strip()
    return jsonify({"proxy": proxy})


@bp.route("/api/mi-accounts/proxy", methods=["POST"])
def api_set_proxy():
    """Set or clear the proxy for Xiaomi API calls.

    JSON body: {"proxy": "socks5://127.0.0.1:1080"} or {"proxy": ""} to clear.
    """
    data = request.json or {}
    proxy = data.get("proxy", "").strip()
    if proxy:
        os.environ["OSMOSIS_PROXY"] = proxy
    else:
        os.environ.pop("OSMOSIS_PROXY", None)
    return jsonify({"ok": True, "proxy": proxy})


@bp.route("/api/mi-accounts/tor", methods=["GET"])
def api_tor_status():
    """Check if Tor is installed and running."""
    installed = shutil.which("tor") is not None
    running = False
    if installed:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", 9050))
            s.close()
            running = True
        except (OSError, ConnectionRefusedError):
            try:
                r = subprocess.run(
                    ["systemctl", "is-active", "tor"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                running = r.stdout.strip() == "active"
            except Exception:
                pass

    return jsonify(
        {
            "installed": installed,
            "running": running,
            "proxy": "socks5://127.0.0.1:9050" if running else None,
        }
    )


@bp.route("/api/mi-accounts/tor/start", methods=["POST"])
def api_tor_start():
    """Start the Tor service."""
    if not shutil.which("tor"):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Tor is not installed. Install it with: sudo apt install tor",
                }
            ),
            400,
        )

    try:
        r = subprocess.run(
            ["sudo", "systemctl", "start", "tor"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode == 0:
            for _ in range(10):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    s.connect(("127.0.0.1", 9050))
                    s.close()
                    os.environ["OSMOSIS_PROXY"] = "socks5://127.0.0.1:9050"
                    return jsonify(
                        {"ok": True, "proxy": "socks5://127.0.0.1:9050"}
                    )
                except (OSError, ConnectionRefusedError):
                    time.sleep(1)
            return jsonify(
                {"ok": False, "error": "Tor started but SOCKS port not ready"}
            )
        return jsonify(
            {"ok": False, "error": r.stderr.strip() or "Failed to start Tor"}
        )
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Timed out starting Tor"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
