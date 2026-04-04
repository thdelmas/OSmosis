"""Samsung stock firmware listing and download via Samsung FUS (Firmware Update Server).

Uses the same protocol as samloader/samfirm to list available firmware versions
and download them directly from Samsung's CDN. Downloaded files are AES-encrypted
by Samsung and decrypted locally.
"""

import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task

bp = Blueprint("samsung_stock", __name__)

# Samsung FUS endpoints
_FUS_BASE = "https://neofussvr.sslcs.cdngc.net"
_FUS_NONCE = f"{_FUS_BASE}/NF_DownloadGenerateNonce.do"
_FUS_BINARY = f"{_FUS_BASE}/NF_DownloadBinaryForMass.do"

# OTA version check (lightweight, no auth needed)
_VERSION_URL = (
    "https://fota-cloud-dn.ospserver.net/firmware/{region}/{model}/version.xml"
)

# Common regions for Samsung devices
_REGIONS = [
    ("XEF", "France"),
    ("BTU", "United Kingdom"),
    ("DBT", "Germany"),
    ("ITV", "Italy"),
    ("PHE", "Spain"),
    ("AUT", "Austria / Switzerland"),
    ("SER", "Russia"),
    ("XEO", "Poland"),
    ("TUR", "Turkey"),
    ("INS", "India"),
    ("XSA", "Australia"),
    ("KOO", "South Korea"),
    ("XAR", "Argentina"),
    ("ZTO", "Brazil"),
    ("XAC", "Canada"),
    ("TMB", "T-Mobile US"),
    ("ATT", "AT&T US"),
    ("VZW", "Verizon US"),
    ("SPR", "Sprint US"),
    ("USC", "US Cellular"),
]


def _check_version(model: str, region: str) -> dict | None:
    """Check the latest firmware version for a model/region pair.

    Returns {version, model, region} or None if not found.
    Uses Samsung's lightweight OTA version endpoint.
    """
    url = _VERSION_URL.format(region=region, model=model)
    try:
        result = subprocess.run(
            ["wget", "-q", "-O", "-", "--timeout=8", url],
            capture_output=True,
            text=True,
            timeout=12,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        root = ET.fromstring(result.stdout)  # noqa: S314
        ver_el = root.find(".//latest")
        if ver_el is None or not ver_el.text:
            return None

        # Version format: PDA/CSC/PHONE/DATA — we want the PDA (main build)
        version = ver_el.text.strip().split("/")[0]
        return {"version": version, "model": model, "region": region}
    except Exception:
        return None


@bp.route("/api/samsung/stock/<model>")
def api_samsung_stock_list(model):
    """List available stock firmware versions for a Samsung model.

    Checks Samsung's OTA servers for each common region. Returns all
    found versions with region info.
    """
    model = model.upper().strip()
    if not re.match(r"^[A-Z]{2}-[A-Z0-9]+$", model) and not re.match(
        r"^GT-[A-Z0-9]+$", model
    ):
        return jsonify({"error": "Invalid Samsung model number"}), 400

    # Check a subset of common regions in parallel-ish via quick sequential calls
    # (each call is ~1s timeout, so checking 20 regions takes ~3-5s with failures)
    versions = []
    seen = set()

    for region_code, region_label in _REGIONS:
        result = _check_version(model, region_code)
        if result and result["version"] not in seen:
            seen.add(result["version"])
            versions.append(
                {
                    "version": result["version"],
                    "region": region_code,
                    "region_label": region_label,
                    "model": model,
                }
            )
        # Also collect same version from different regions
        elif result and result["version"] in seen:
            # Add the region as an alternative for an already-seen version
            for v in versions:
                if v["version"] == result["version"]:
                    if "alt_regions" not in v:
                        v["alt_regions"] = []
                    v["alt_regions"].append(
                        {"region": region_code, "label": region_label}
                    )
                    break

    return jsonify(
        {
            "model": model,
            "versions": versions,
            "regions_checked": len(_REGIONS),
        }
    )


@bp.route("/api/samsung/stock/download", methods=["POST"])
def api_samsung_stock_download():
    """Download Samsung stock firmware using samloader (or manual URL).

    Accepts either:
      - {model, region, version}: auto-download via samloader if installed
      - {url, model}: direct download from a firmware URL

    Falls back to guiding the user to samfw.com if automated download
    isn't available.
    """
    model = (request.json.get("model", "") or "").upper().strip()
    region = (request.json.get("region", "") or "").upper().strip()
    version = request.json.get("version", "")
    url = request.json.get("url", "")

    if not model:
        return jsonify({"error": "Model number required"}), 400

    codename = model.lower().replace("-", "")
    target = Path.home() / "Osmosis-downloads" / codename
    filename = (
        f"{model}_{region}_{version}.zip" if version else f"{model}_stock.zip"
    )
    filename = re.sub(r"[^\w.\-]", "_", filename)
    dest = str(target / filename)

    # Check if already downloaded
    if Path(dest).is_file() and Path(dest).stat().st_size > 1_000_000:
        return jsonify(
            {
                "status": "exists",
                "dest": dest,
                "size_mb": round(Path(dest).stat().st_size / 1_048_576, 1),
            }
        )

    def _run(task: Task):
        target.mkdir(parents=True, exist_ok=True)

        # Strategy 1: Use samloader if installed
        has_samloader = (
            subprocess.run(
                ["samloader", "--help"],
                capture_output=True,
                timeout=5,
            ).returncode
            == 0
            if _cmd_exists("samloader")
            else False
        )

        if has_samloader and region and version:
            task.emit(
                f"Downloading {model} firmware ({region}, {version}) via samloader..."
            )
            task.emit(f"Destination: {dest}")

            # Step 1: Check binary availability
            task.emit(
                "Checking firmware availability on Samsung servers...", "info"
            )
            rc = task.run_shell(
                [
                    "samloader",
                    "-m",
                    model,
                    "-r",
                    region,
                    "checkupdate",
                ]
            )
            if rc != 0:
                task.emit(
                    "Firmware not found on Samsung servers for this region.",
                    "warn",
                )
                task.emit(
                    f"Try downloading manually from: https://samfw.com/firmware/{model}",
                    "info",
                )
                task.done(False)
                return

            # Step 2: Download
            task.emit("Downloading firmware from Samsung CDN...", "info")
            task.emit(
                "This may take a while depending on your connection speed.",
                "info",
            )
            rc = task.run_shell(
                [
                    "samloader",
                    "-m",
                    model,
                    "-r",
                    region,
                    "download",
                    "-v",
                    version,
                    "-O",
                    dest,
                ]
            )
            if rc != 0:
                task.emit("Download failed.", "error")
                Path(dest).unlink(missing_ok=True)
                task.emit(
                    f"Try downloading manually from: https://samfw.com/firmware/{model}",
                    "info",
                )
                task.done(False)
                return

            # Step 3: Decrypt if needed (samloader downloads are encrypted)
            enc_path = dest + ".enc2" if not Path(dest).exists() else None
            if enc_path and Path(enc_path).exists():
                task.emit("Decrypting firmware...", "info")
                rc = task.run_shell(
                    [
                        "samloader",
                        "-m",
                        model,
                        "-r",
                        region,
                        "decrypt",
                        "-v",
                        version,
                        "-i",
                        enc_path,
                        "-o",
                        dest,
                    ]
                )
                Path(enc_path).unlink(missing_ok=True)
                if rc != 0:
                    task.emit("Decryption failed.", "error")
                    task.done(False)
                    return

        # Strategy 2: Direct URL download
        elif url:
            task.emit(f"Downloading firmware from: {url}")
            task.emit(f"Destination: {dest}")
            rc = task.run_shell(
                ["wget", "--progress=dot:giga", "-O", dest, url]
            )
            if rc != 0:
                task.emit("Download failed.", "error")
                Path(dest).unlink(missing_ok=True)
                task.done(False)
                return

        # Strategy 3: No automated download available
        else:
            task.emit(
                "Automated Samsung firmware download is not available.", "warn"
            )
            task.emit("", "info")
            task.emit("To download stock firmware manually:", "info")
            task.emit(f"  1. Visit https://samfw.com/firmware/{model}", "info")
            task.emit(f"  2. Select region: {region or 'your region'}", "info")
            task.emit("  3. Download the firmware ZIP", "info")
            task.emit(
                "  4. Save it and use the 'Restore stock firmware' option with the file path",
                "info",
            )
            task.done(False)
            return

        # Verify download
        if Path(dest).exists() and Path(dest).stat().st_size > 1_000_000:
            size_mb = round(Path(dest).stat().st_size / 1_048_576, 1)
            task.emit(f"Download complete ({size_mb} MB).", "success")
            task.emit(f"Saved to: {dest}", "success")
            task.done(True)
        else:
            task.emit("Downloaded file is missing or too small.", "error")
            Path(dest).unlink(missing_ok=True)
            task.done(False)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id, "dest": dest})


def _cmd_exists(name: str) -> bool:
    """Check if a command exists on the system."""
    import shutil

    return shutil.which(name) is not None
