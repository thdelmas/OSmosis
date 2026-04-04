"""ADB device action routes — reboot, shell commands."""

import subprocess

from flask import Blueprint, jsonify, request

from web.core import cmd_exists

bp = Blueprint("device_actions", __name__)

_REBOOT_TARGETS = {
    "system": [],
    "bootloader": ["bootloader"],
    "recovery": ["recovery"],
    "download": ["download"],
    "fastboot": ["bootloader"],
    "edl": ["edl"],
}


@bp.route("/api/adb/reboot", methods=["POST"])
def api_adb_reboot():
    """Reboot a device via ADB to a specified target.

    JSON body: {"target": "system|bootloader|recovery|download|fastboot|edl"}
    Works from normal ADB, recovery, and sideload modes.
    """
    if not cmd_exists("adb"):
        return jsonify({"ok": False, "error": "adb is not installed"}), 503

    target = (request.json or {}).get("target", "system")
    args = _REBOOT_TARGETS.get(target)
    if args is None:
        return jsonify(
            {"ok": False, "error": f"Invalid reboot target: {target}"}
        ), 400

    cmd = ["adb", "reboot"] + args

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        ok = result.returncode == 0
        if not ok:
            # Fallback: try adb shell reboot for stubborn sideload modes
            fallback = subprocess.run(
                ["adb", "shell", "reboot"] + args,
                capture_output=True,
                text=True,
                timeout=10,
            )
            ok = fallback.returncode == 0

        return jsonify(
            {
                "ok": ok,
                "target": target,
                "message": f"Rebooting to {target}..."
                if ok
                else "Reboot command failed.",
            }
        )
    except subprocess.TimeoutExpired:
        return jsonify(
            {"ok": False, "message": "Reboot command timed out."}
        ), 504
    except OSError as e:
        return jsonify({"ok": False, "message": str(e)}), 500
