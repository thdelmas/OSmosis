"""Device submission routes — submit, list, and approve new device profiles."""

import re

from flask import Blueprint, jsonify, request

bp = Blueprint("device_submissions", __name__)

_SUBMISSIONS_DIR = __import__("pathlib").Path.home() / ".osmosis" / "device-submissions"


@bp.route("/api/devices/submit", methods=["POST"])
def api_devices_submit():
    """Submit a new device profile for inclusion in the database.

    JSON body: {
        "category": "phone" | "scooter" | "ebike" | "microcontroller",
        "label": "Galaxy Tab S 10.5",
        "model": "SM-T805",
        "codename": "chagallltex",
        "brand": "Samsung",
        ... (additional fields depending on category)
    }

    Submissions are saved to ~/.osmosis/device-submissions/ for review.
    """
    import json
    from datetime import datetime

    body = request.json or {}
    category = body.get("category", "").strip()
    label = body.get("label", "").strip()

    if not category:
        return jsonify({"error": "category is required"}), 400
    if category not in ("phone", "scooter", "ebike", "microcontroller"):
        return jsonify({"error": "Invalid category"}), 400
    if not label:
        return jsonify({"error": "label is required"}), 400

    _SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_label = re.sub(r"[^a-zA-Z0-9_-]", "_", label)[:40]
    filename = f"{category}-{safe_label}-{timestamp}.json"

    submission = {
        "submitted_at": datetime.now().isoformat(),
        "category": category,
        **body,
    }

    (_SUBMISSIONS_DIR / filename).write_text(json.dumps(submission, indent=2) + "\n")

    return jsonify({"ok": True, "filename": filename}), 201


@bp.route("/api/devices/submissions")
def api_devices_submissions():
    """List pending device submissions."""
    import json

    if not _SUBMISSIONS_DIR.exists():
        return jsonify([])

    submissions = []
    for f in sorted(_SUBMISSIONS_DIR.iterdir(), reverse=True):
        if f.suffix != ".json":
            continue
        try:
            data = json.loads(f.read_text())
            data["_filename"] = f.name
            submissions.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    return jsonify(submissions)


@bp.route("/api/devices/submissions/approve", methods=["POST"])
def api_devices_submissions_approve():
    """Approve a submission and append it to the appropriate config file.

    JSON body: {"filename": "phone-Galaxy_Tab-20260321-120000.json"}
    """
    import json

    from web.core import SCRIPT_DIR

    body = request.json or {}
    filename = body.get("filename", "")
    if not filename:
        return jsonify({"error": "filename is required"}), 400

    sub_path = _SUBMISSIONS_DIR / filename
    if not sub_path.is_file():
        return jsonify({"error": "Submission not found"}), 404

    try:
        data = json.loads(sub_path.read_text())
    except (json.JSONDecodeError, OSError):
        return jsonify({"error": "Invalid submission file"}), 400

    category = data.get("category", "")

    if category == "phone":
        cfg_file = SCRIPT_DIR / "devices.cfg"
        line = "|".join(
            [
                data.get("id", data.get("codename", "unknown")),
                data.get("label", ""),
                data.get("model", ""),
                data.get("codename", ""),
                data.get("rom_url", ""),
                data.get("twrp_url", ""),
                data.get("eos_url", ""),
                data.get("stock_url", ""),
                data.get("gapps_url", ""),
            ]
        )
    elif category == "scooter":
        cfg_file = SCRIPT_DIR / "scooters.cfg"
        line = "|".join(
            [
                data.get("id", ""),
                data.get("label", ""),
                data.get("brand", ""),
                data.get("model_number", ""),
                data.get("protocol", "ninebot"),
                data.get("flash_method", "ble"),
                data.get("cfw_url", ""),
                data.get("shfw_supported", "no"),
                data.get("notes", ""),
            ]
        )
    elif category == "ebike":
        cfg_file = SCRIPT_DIR / "ebikes.cfg"
        line = "|".join(
            [
                data.get("id", ""),
                data.get("label", ""),
                data.get("brand", ""),
                data.get("controller", ""),
                data.get("flash_method", "stlink"),
                data.get("fw_project", ""),
                data.get("fw_url", ""),
                data.get("support_status", "experimental"),
                data.get("notes", ""),
            ]
        )
    elif category == "microcontroller":
        cfg_file = SCRIPT_DIR / "microcontrollers.cfg"
        line = "|".join(
            [
                data.get("id", ""),
                data.get("label", ""),
                data.get("brand", ""),
                data.get("arch", ""),
                data.get("flash_tool", ""),
                data.get("flash_args", ""),
                data.get("bootloader", ""),
                data.get("usb_vid", ""),
                data.get("usb_pid", ""),
                data.get("notes", ""),
            ]
        )
    else:
        return jsonify({"error": f"Unknown category: {category}"}), 400

    with open(cfg_file, "a") as f:
        f.write(line + "\n")

    # Move submission to approved
    approved_dir = _SUBMISSIONS_DIR / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)
    sub_path.rename(approved_dir / filename)

    return jsonify({"ok": True, "config_file": str(cfg_file), "line": line})
