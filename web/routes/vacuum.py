"""Robot vacuum routes — Valetudo install via DustBuilder and UART.

Guides the user through generating a rooted firmware image via DustBuilder,
verifying model/hardware compatibility, and flashing via OTA or UART.
"""

from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("vacuum", __name__)

# Known vacuum models and their DustBuilder compatibility
_VACUUM_MODELS = {
    # Roborock
    "roborock.vacuum.s5": {
        "name": "Roborock S5",
        "brand": "Roborock",
        "soc": "Allwinner R16",
        "valetudo": True,
        "dustbuilder": True,
        "flash_methods": ["ota", "uart"],
        "status": "research",
    },
    "roborock.vacuum.s5e": {
        "name": "Roborock S5 Max",
        "brand": "Roborock",
        "soc": "Allwinner R16",
        "valetudo": True,
        "dustbuilder": True,
        "flash_methods": ["ota", "uart"],
        "status": "research",
    },
    "roborock.vacuum.s6": {
        "name": "Roborock S6",
        "brand": "Roborock",
        "soc": "Allwinner R16",
        "valetudo": True,
        "dustbuilder": True,
        "flash_methods": ["ota", "uart"],
        "status": "research",
    },
    "roborock.vacuum.a08": {
        "name": "Roborock S6 Pure",
        "brand": "Roborock",
        "soc": "Allwinner R16",
        "valetudo": True,
        "dustbuilder": True,
        "flash_methods": ["ota"],
        "status": "research",
    },
    "roborock.vacuum.a15": {
        "name": "Roborock S7",
        "brand": "Roborock",
        "soc": "Rockchip",
        "valetudo": True,
        "dustbuilder": True,
        "flash_methods": ["ota", "uart"],
        "status": "research",
    },
    "roborock.vacuum.a27": {
        "name": "Roborock Q7 Max",
        "brand": "Roborock",
        "soc": "Rockchip",
        "valetudo": True,
        "dustbuilder": True,
        "flash_methods": ["ota"],
        "status": "research",
    },
    # Dreame
    "dreame.vacuum.p2029": {
        "name": "Dreame L10 Pro",
        "brand": "Dreame",
        "soc": "Allwinner",
        "valetudo": True,
        "dustbuilder": True,
        "flash_methods": ["ota", "uart"],
        "status": "research",
    },
    "dreame.vacuum.r2228o": {
        "name": "Dreame D9 Pro",
        "brand": "Dreame",
        "soc": "Allwinner",
        "valetudo": True,
        "dustbuilder": True,
        "flash_methods": ["ota"],
        "status": "research",
    },
    # Xiaomi (Mi Robot Vacuum)
    "rockrobo.vacuum.v1": {
        "name": "Xiaomi Mi Robot Vacuum (Gen 1)",
        "brand": "Xiaomi",
        "soc": "Allwinner R16",
        "valetudo": True,
        "dustbuilder": True,
        "flash_methods": ["ota", "uart"],
        "status": "research",
    },
}


@bp.route("/api/vacuum/models")
def api_vacuum_models():
    """Return all known robot vacuum models with Valetudo support info."""
    brand = request.args.get("brand", "").lower().strip()
    models = []
    for model_id, info in _VACUUM_MODELS.items():
        if brand and brand not in info["brand"].lower():
            continue
        models.append({"id": model_id, **info})
    return jsonify(models)


@bp.route("/api/vacuum/check-model")
def api_vacuum_check_model():
    """Check if a specific vacuum model is supported.

    Query params:
        model: vacuum model identifier (e.g. roborock.vacuum.s5)
    """
    model = request.args.get("model", "").strip()
    if not model:
        return jsonify({"error": "No model specified"}), 400

    info = _VACUUM_MODELS.get(model)
    if not info:
        return (
            jsonify(
                {
                    "supported": False,
                    "model": model,
                    "hint": "Model not found in the supported list. Check the "
                    "model identifier on the sticker under your vacuum "
                    "(e.g. roborock.vacuum.s5). Newer models may not be supported.",
                }
            ),
            404,
        )

    return jsonify({"supported": True, "model": model, **info})


@bp.route("/api/vacuum/flash-guide", methods=["POST"])
def api_vacuum_flash_guide():
    """Generate a step-by-step flash guide for a vacuum model.

    JSON body: {
        "model": "roborock.vacuum.s5",
        "method": "ota"  // or "uart"
    }
    """
    body = request.json or {}
    model = body.get("model", "").strip()
    method = body.get("method", "ota").strip()

    info = _VACUUM_MODELS.get(model)
    if not info:
        return jsonify({"error": "Unsupported model"}), 404

    if method not in info["flash_methods"]:
        return (
            jsonify(
                {
                    "error": f"Method '{method}' not available for this model",
                    "available": info["flash_methods"],
                }
            ),
            400,
        )

    steps = []

    # Common first steps
    steps.append(
        {
            "id": "verify-model",
            "title": "Verify your model",
            "desc": f"Confirm your vacuum is a **{info['name']}** "
            f"(model: {model}). Check the sticker on the bottom of the vacuum. "
            "Hardware revisions matter — a model that works on one revision "
            "may be locked on another.",
        }
    )

    if info["dustbuilder"]:
        steps.append(
            {
                "id": "dustbuilder",
                "title": "Generate rooted firmware via DustBuilder",
                "desc": "Go to **builder.dontvacuum.me** and enter your vacuum's "
                "model and (optionally) serial number. DustBuilder will generate "
                "a custom rooted firmware image with Valetudo pre-installed. "
                "Download the resulting .pkg file.",
                "url": "https://builder.dontvacuum.me/",
            }
        )

    if method == "ota":
        steps.append(
            {
                "id": "flash-ota",
                "title": "Flash via OTA update",
                "desc": "Use the vacuum manufacturer's app (Mi Home or Roborock) "
                "to push the DustBuilder image as a firmware update. Some models "
                "require a local OTA push tool (e.g. python-miio). Follow the "
                "DustBuilder instructions for your specific model.",
            }
        )
    elif method == "uart":
        steps.append(
            {
                "id": "uart-access",
                "title": "Connect via UART",
                "desc": "Open the vacuum's top shell. Locate the UART header on "
                "the mainboard (usually 4 pins: GND, TX, RX, 3.3V). Connect a "
                "3.3V USB-to-serial adapter (e.g. CP2102 or FTDI). **Do NOT use "
                "5V — it will damage the board.**",
            }
        )
        steps.append(
            {
                "id": "flash-uart",
                "title": "Flash via UART console",
                "desc": "Open a serial terminal (115200 baud). Interrupt U-Boot "
                "to get a shell. Transfer the firmware image via TFTP or USB, "
                "then write it to the correct partition.",
            }
        )

    steps.append(
        {
            "id": "valetudo-setup",
            "title": "Set up Valetudo",
            "desc": "After the vacuum reboots with the new firmware, connect to "
            "its WiFi hotspot (or find it on your network). Open the Valetudo "
            "web UI at http://<vacuum-ip>. Configure WiFi, MQTT, and map "
            "settings. Your vacuum now runs 100% locally.",
            "url": "https://valetudo.cloud/",
        }
    )

    return jsonify(
        {
            "model": model,
            "name": info["name"],
            "method": method,
            "steps": steps,
        }
    )


@bp.route("/api/vacuum/verify-firmware", methods=["POST"])
def api_vacuum_verify_firmware():
    """Verify a downloaded vacuum firmware image.

    JSON body: { "fw_path": "/path/to/firmware.pkg" }
    """
    body = request.json or {}
    fw_path = body.get("fw_path", "").strip()

    if not fw_path or not Path(fw_path).is_file():
        return jsonify({"error": "Firmware file not found"}), 400

    import hashlib

    p = Path(fw_path)
    size = p.stat().st_size
    h = hashlib.sha256(p.read_bytes()).hexdigest()

    return jsonify(
        {
            "path": fw_path,
            "filename": p.name,
            "size": size,
            "size_human": f"{size // (1024 * 1024)}MB" if size >= 1024 * 1024 else f"{size // 1024}KB",
            "sha256": h,
            "looks_valid": size > 1024 * 1024,  # vacuum FW is typically >10MB
        }
    )
