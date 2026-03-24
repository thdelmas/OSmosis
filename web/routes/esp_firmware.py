"""ESP firmware catalog — first-class flash targets for ESP32/ESP8266.

Provides a firmware catalog (Tasmota, ESPHome, WLED, Meshtastic) and a
download endpoint so the microcontroller wizard can offer one-click
firmware selection for ESP boards.
"""

import hashlib
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from web.core import parse_microcontrollers_cfg

bp = Blueprint("esp_firmware", __name__)

# Chip-to-Tasmota variant mapping.  Tasmota publishes per-chip binaries.
_TASMOTA_CHIP_MAP = {
    "esp32": "tasmota32.bin",
    "esp32s2": "tasmota32s2.bin",
    "esp32s3": "tasmota32s3.bin",
    "esp32c3": "tasmota32c3.bin",
    "esp32c6": "tasmota32c6.bin",
    "esp8266": "tasmota.bin",
}

_TASMOTA_BASE = "https://ota.tasmota.com/tasmota32/release"
_TASMOTA_8266_BASE = "https://ota.tasmota.com/tasmota/release"


def esp_firmware_targets(chip: str) -> list[dict]:
    """Return available firmware targets for the given ESP chip variant."""
    chip = chip.lower().replace("--chip ", "").strip()
    targets: list[dict] = []

    # Tasmota
    tasmota_file = _TASMOTA_CHIP_MAP.get(chip)
    if tasmota_file:
        base = _TASMOTA_8266_BASE if chip == "esp8266" else _TASMOTA_BASE
        targets.append(
            {
                "id": "tasmota",
                "name": "Tasmota",
                "desc": "Open-source smart home firmware. Supports MQTT, Home Assistant, and web UI.",
                "url": f"{base}/{tasmota_file}",
                "filename": tasmota_file,
                "tags": ["smart-home", "mqtt", "home-assistant"],
                "homepage": "https://tasmota.github.io/",
            }
        )

    # ESPHome — stub firmware (user customizes via YAML, but we can flash
    # the initial ESPHome dashboard image so the device appears on the network)
    if chip in ("esp32", "esp32s2", "esp32s3", "esp32c3", "esp8266"):
        targets.append(
            {
                "id": "esphome",
                "name": "ESPHome",
                "desc": "YAML-configured firmware for Home Assistant. Flash the base image, then adopt from the ESPHome dashboard.",
                "url": None,
                "note": "ESPHome firmware is built per-device from YAML configs. Use the ESPHome dashboard or CLI to compile and flash.",
                "tags": ["smart-home", "home-assistant", "yaml"],
                "homepage": "https://esphome.io/",
            }
        )

    # WLED
    if chip in ("esp32", "esp32s3", "esp32c3", "esp8266"):
        wled_file = "WLED_0.15.0_ESP32.bin" if chip != "esp8266" else "WLED_0.15.0_ESP8266.bin"
        targets.append(
            {
                "id": "wled",
                "name": "WLED",
                "desc": "LED strip controller with 100+ effects, web UI, and Home Assistant integration.",
                "url": f"https://github.com/Aircoookie/WLED/releases/latest/download/{wled_file}",
                "filename": wled_file,
                "tags": ["led", "effects", "smart-home"],
                "homepage": "https://kno.wled.ge/",
            }
        )

    # Meshtastic (ESP32 + LoRa boards)
    if chip in ("esp32", "esp32s3"):
        targets.append(
            {
                "id": "meshtastic",
                "name": "Meshtastic",
                "desc": "Off-grid mesh networking over LoRa. Requires an ESP32 board with a LoRa radio.",
                "url": None,
                "note": "Meshtastic firmware varies by board. Download the correct build from the Meshtastic flasher or GitHub releases.",
                "tags": ["mesh", "lora", "off-grid"],
                "homepage": "https://meshtastic.org/",
            }
        )

    return targets


@bp.route("/api/microcontrollers/firmware-targets")
def api_firmware_targets():
    """Return available firmware targets for an ESP board.

    Query params:
        board_id: preset ID from microcontrollers.cfg
        chip: ESP chip name (e.g. esp32, esp32s3, esp8266)

    At least one of board_id or chip must be provided.
    """
    board_id = request.args.get("board_id", "").strip()
    chip = request.args.get("chip", "").strip()

    if board_id and not chip:
        board = next(
            (b for b in parse_microcontrollers_cfg() if b["id"] == board_id),
            None,
        )
        if not board:
            return jsonify({"error": f"Board '{board_id}' not found"}), 404
        # Extract chip from flash_args (e.g. "--chip esp32s3")
        args = board.get("flash_args", "")
        if "--chip" in args:
            chip = args.split("--chip")[-1].strip().split()[0]
        elif board["arch"] in ("esp32", "esp8266"):
            chip = board["arch"]

    if not chip:
        return jsonify({"error": "Cannot determine chip type"}), 400

    return jsonify(esp_firmware_targets(chip))


@bp.route("/api/microcontrollers/download-firmware", methods=["POST"])
def api_download_firmware():
    """Download a firmware binary from a URL.

    JSON body: { "url": "https://...", "filename": "tasmota32.bin" }

    Returns: { "path": "/home/.../Osmosis-downloads/firmware/tasmota32.bin",
               "size": 1234567, "sha256": "abc..." }
    """
    body = request.json or {}
    url = body.get("url", "").strip()
    filename = body.get("filename", "").strip()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return jsonify({"error": "Only HTTP/HTTPS URLs are supported"}), 400

    if not filename:
        filename = Path(parsed.path).name or "firmware.bin"

    dl_dir = Path.home() / "Osmosis-downloads" / "firmware"
    dl_dir.mkdir(parents=True, exist_ok=True)
    dest = dl_dir / filename

    try:
        result = subprocess.run(
            ["curl", "-fSL", "--max-time", "120", "-o", str(dest), url],
            capture_output=True,
            text=True,
            timeout=130,
        )
        if result.returncode != 0:
            return (
                jsonify({"error": f"Download failed: {result.stderr.strip()}"}),
                502,
            )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Download timed out"}), 504

    if not dest.is_file() or dest.stat().st_size < 1024:
        return jsonify({"error": "Downloaded file is too small or missing"}), 502

    h = hashlib.sha256(dest.read_bytes()).hexdigest()
    size = dest.stat().st_size

    return jsonify(
        {
            "path": str(dest),
            "filename": filename,
            "size": size,
            "size_human": f"{size // (1024 * 1024)}MB" if size >= 1024 * 1024 else f"{size // 1024}KB",
            "sha256": h,
        }
    )
