"""Device detection, diagnostics, and USB device parsing routes."""

import re
import subprocess

from flask import Blueprint, jsonify, request

from web.core import _MODEL_NAMES, Task, cmd_exists, parse_devices_cfg, start_task

bp = Blueprint("device", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_usb_devices() -> list[dict]:
    """Return list of phone-like USB devices from lsusb, with friendly names."""
    phone_vendors = {
        "04e8": "Samsung",
        "18d1": "Google",
        "1004": "LG",
        "2717": "Xiaomi",
        "22b8": "Motorola",
        "0bb4": "HTC",
        "2a70": "OnePlus",
        "12d1": "Huawei",
        "2ae5": "Fairphone",
        "0fce": "Sony",
        "1949": "Amazon",
        "2b4c": "Nothing",
    }
    devices = []
    try:
        lsusb = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        for line in lsusb.stdout.strip().splitlines():
            low = line.lower()
            for vid, brand in phone_vendors.items():
                if vid in low:
                    raw = line
                    id_pos = line.find("ID ")
                    if id_pos != -1:
                        after_id = line[id_pos + 4 :]
                        space = after_id.find(" ")
                        raw = after_id[space + 1 :].strip() if space != -1 else after_id

                    name = re.sub(
                        r"\b(Inc\.?|Co\.?,?\s*Ltd\.?|Corp\.?|Electronics|Technology|Communication)\b",
                        "",
                        raw,
                        flags=re.IGNORECASE,
                    )
                    name = re.sub(r"\([^)]*\)", "", name)
                    name = re.sub(r"\b(misc\.?|series)\b", "", name, flags=re.IGNORECASE)
                    name = re.sub(r"[,\s]+", " ", name).strip().strip(",").strip()
                    if not name or name.lower() == brand.lower():
                        name = brand

                    devices.append({"vendor": brand, "name": name})
                    break
    except Exception:
        pass
    return devices


def _get_adb_prop(serial: str, prop: str) -> str:
    """Get a single Android system property via adb."""
    return subprocess.run(
        ["adb", "-s", serial, "shell", "getprop", prop],
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.strip()


def _query_adb_device(serial: str) -> dict:
    """Query a single ADB device by serial for model/codename info."""
    model = _get_adb_prop(serial, "ro.product.model")
    codename = _get_adb_prop(serial, "ro.product.device")
    if not codename:
        codename = _get_adb_prop(serial, "ro.product.board")

    brand = _get_adb_prop(serial, "ro.product.brand").capitalize()
    marketing = _get_adb_prop(serial, "ro.product.marketname")
    if not marketing:
        marketing = _get_adb_prop(serial, "ro.config.marketing_name")
    if not marketing:
        marketing = _MODEL_NAMES.get(model, "")

    display_name = marketing or model
    if brand and not display_name.lower().startswith(brand.lower()):
        display_name = f"{brand} {display_name}"

    match = None
    for dev in parse_devices_cfg():
        if dev["model"].lower() == model.lower() or dev["codename"].lower() == codename.lower():
            match = dev
            break

    return {
        "serial": serial,
        "model": model,
        "codename": codename,
        "display_name": display_name,
        "match": match,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.route("/api/devices")
def api_devices():
    return jsonify(parse_devices_cfg())


@bp.route("/api/detect")
def api_detect():
    """Auto-detect connected device via adb."""
    if not cmd_exists("adb"):
        return jsonify({"error": "adb not installed"}), 500

    try:
        dev_list = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        dev_lines = [
            line
            for line in dev_list.stdout.strip().splitlines()[1:]
            if line.strip() and ("device" in line.split("\t")[-1:] or "recovery" in line.split("\t")[-1:])
        ]
        if not dev_lines:
            usb_devices = _parse_usb_devices()
            if usb_devices:
                return jsonify({"error": "usb_no_adb", "usb_devices": usb_devices}), 404
            return jsonify({"error": "no_device"}), 404

        serials = [line.split("\t")[0] for line in dev_lines]
        detected = [_query_adb_device(s) for s in serials]

        if len(detected) == 1:
            d = detected[0]
            return jsonify(
                {
                    "model": d["model"],
                    "codename": d["codename"],
                    "display_name": d["display_name"],
                    "match": d["match"],
                }
            )
        else:
            return jsonify({"multiple": True, "devices": detected})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/diagnostics")
def api_diagnostics():
    """Query connected device for detailed diagnostics via ADB."""
    if not cmd_exists("adb"):
        return jsonify({"error": "adb not installed"}), 500

    try:
        dev_list = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        dev_lines = [
            line
            for line in dev_list.stdout.strip().splitlines()[1:]
            if line.strip() and "device" in line.split("\t")[-1:]
        ]
        if not dev_lines:
            return jsonify({"error": "no_device"}), 404

        serial = dev_lines[0].split("\t")[0]

        def prop(name):
            return subprocess.run(
                ["adb", "-s", serial, "shell", "getprop", name],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()

        def shell(cmd):
            return subprocess.run(
                ["adb", "-s", serial, "shell", cmd],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()

        # Battery info
        battery_raw = shell("dumpsys battery")
        battery = {}
        for bline in battery_raw.splitlines():
            bline = bline.strip()
            if ":" in bline:
                k, _, v = bline.partition(":")
                battery[k.strip().lower().replace(" ", "_")] = v.strip()

        # Storage info
        storage_raw = shell("df /data 2>/dev/null | tail -1")
        storage = {}
        if storage_raw:
            parts = storage_raw.split()
            if len(parts) >= 4:
                try:
                    total = int(parts[1]) * 1024
                    used = int(parts[2]) * 1024
                    free = int(parts[3]) * 1024
                    storage = {"total": total, "used": used, "free": free}
                except ValueError:
                    pass

        os_info = {
            "android_version": prop("ro.build.version.release"),
            "sdk": prop("ro.build.version.sdk"),
            "security_patch": prop("ro.build.version.security_patch"),
            "build_id": prop("ro.build.display.id"),
            "build_type": prop("ro.build.type"),
            "build_date": prop("ro.build.date"),
        }

        brand = prop("ro.product.brand").capitalize()
        model = prop("ro.product.model")
        codename = prop("ro.product.device") or prop("ro.product.board")
        marketing = prop("ro.product.marketname") or prop("ro.config.marketing_name")
        display_name = marketing or _MODEL_NAMES.get(model, model)
        if brand and not display_name.lower().startswith(brand.lower()):
            display_name = f"{brand} {display_name}"

        bootloader = prop("ro.boot.flash.locked")
        bootloader_status = "locked" if bootloader == "1" else ("unlocked" if bootloader == "0" else "unknown")
        if bootloader_status == "unknown":
            oem = prop("ro.boot.verifiedbootstate")
            if oem == "orange":
                bootloader_status = "unlocked"
            elif oem == "green":
                bootloader_status = "locked"

        root_check = subprocess.run(
            ["adb", "-s", serial, "shell", "su", "-c", "id"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_root = "uid=0" in root_check.stdout

        pm_list = shell("pm list packages 2>/dev/null")
        has_magisk = "com.topjohnwu.magisk" in pm_list or "io.github.vvb2060.magisk" in pm_list

        rom_name = ""
        lineage_ver = prop("ro.lineage.version")
        eos_ver = prop("ro.e.version")
        if lineage_ver:
            rom_name = f"LineageOS {lineage_ver}"
        elif eos_ver:
            rom_name = f"/e/OS {eos_ver}"
        else:
            rom_name = prop("ro.build.flavor") or f"Android {os_info['android_version']}"

        uptime_raw = shell("cat /proc/uptime 2>/dev/null")
        uptime_secs = 0
        if uptime_raw:
            try:
                uptime_secs = int(float(uptime_raw.split()[0]))
            except (ValueError, IndexError):
                pass

        return jsonify(
            {
                "serial": serial,
                "display_name": display_name,
                "brand": brand,
                "model": model,
                "codename": codename,
                "battery": {
                    "level": int(battery.get("level", 0)),
                    "status": battery.get("status", "unknown"),
                    "health": battery.get("health", "unknown"),
                    "temperature": round(int(battery.get("temperature", 0)) / 10, 1),
                    "voltage": round(int(battery.get("voltage", 0)) / 1000, 2),
                    "technology": battery.get("technology", ""),
                },
                "storage": storage,
                "os": os_info,
                "rom_name": rom_name,
                "bootloader": bootloader_status,
                "has_root": has_root,
                "has_magisk": has_magisk,
                "uptime_seconds": uptime_secs,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/configure-rom", methods=["POST"])
def api_configure_rom():
    """Apply post-install configuration via ADB after ROM is installed."""
    config = request.json or {}

    def _run(task: Task):
        task.emit("Applying post-install configuration...", "info")

        task.emit("Waiting for device to come online...", "info")
        rc = task.run_shell(["adb", "wait-for-device"])
        if rc != 0:
            task.emit("Device not found.", "error")
            task.done(False)
            return

        import time

        time.sleep(5)

        debloat = config.get("debloat", [])
        if debloat:
            task.emit("")
            task.emit("=== Removing bloatware ===", "info")
            for pkg in debloat:
                task.emit(f"Disabling {pkg}...")
                rc = task.run_shell(["adb", "shell", "pm", "uninstall", "-k", "--user", "0", pkg])
                if rc != 0:
                    task.run_shell(["adb", "shell", "pm", "disable-user", "--user", "0", pkg])

        privacy = config.get("privacy", {})
        if privacy:
            task.emit("")
            task.emit("=== Applying privacy settings ===", "info")
            if privacy.get("disable_analytics"):
                task.emit("Disabling usage analytics...")
                task.run_shell(["adb", "shell", "settings", "put", "global", "upload_apk_enable", "0"])
                task.run_shell(["adb", "shell", "settings", "put", "secure", "send_action_app_error", "0"])
            if privacy.get("disable_location_history"):
                task.emit("Disabling location history...")
                task.run_shell(["adb", "shell", "settings", "put", "secure", "location_mode", "0"])
            if privacy.get("disable_backup"):
                task.emit("Disabling cloud backup...")
                task.run_shell(["adb", "shell", "settings", "put", "secure", "backup_enabled", "0"])

        locale = config.get("locale", "")
        if locale:
            task.emit("")
            task.emit(f"=== Setting locale: {locale} ===", "info")
            task.run_shell(["adb", "shell", "settings", "put", "system", "system_locales", locale])

        timezone = config.get("timezone", "")
        if timezone:
            task.emit(f"Setting timezone: {timezone}")
            task.run_shell(["adb", "shell", "settings", "put", "global", "auto_time_zone", "0"])
            task.run_shell(["adb", "shell", "setprop", "persist.sys.timezone", timezone])

        display = config.get("display", {})
        if display:
            task.emit("")
            task.emit("=== Applying display settings ===", "info")
            if display.get("dark_mode"):
                task.emit("Enabling dark mode...")
                task.run_shell(["adb", "shell", "cmd", "uimode", "night", "yes"])
            font_scale = display.get("font_scale")
            if font_scale:
                task.emit(f"Setting font scale: {font_scale}")
                task.run_shell(["adb", "shell", "settings", "put", "system", "font_scale", str(font_scale)])

        task.emit("")
        task.emit("Configuration applied!", "success")
        task.done(True)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
