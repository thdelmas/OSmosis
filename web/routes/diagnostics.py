"""Device diagnostics and post-install configuration routes."""

import subprocess

from flask import Blueprint, jsonify, request

from web.core import _MODEL_NAMES, Task, cmd_exists, start_task

bp = Blueprint("diagnostics", __name__)


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
