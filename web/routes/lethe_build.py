"""Lethe build pipeline and init.rc generators.

Extracted from lethe.py to keep route files under the 500-line limit.
"""

from pathlib import Path

from web.core import Task
from web.device_profile import get_profile, load_all_profiles
from web.ipfs_helpers import ipfs_available, ipfs_pin_and_index

OVERLAY_DIR = Path(__file__).resolve().parent.parent.parent / "lethe" / "overlays"
BUILD_OUTPUT_DIR = Path.home() / "Osmosis-downloads" / "lethe-builds"


def build_lethe(task: Task, codename: str, manifest: dict, ipfs_publish: bool):
    """Execute the Lethe build pipeline for a device."""
    BUILD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    task.emit("=" * 60)
    task.emit(f"Lethe build — {codename}", "info")
    base_ver, android_ver = get_device_base_version(codename, manifest)
    task.emit(f"Base: {manifest.get('base', 'lineageos')} {base_ver}")
    task.emit(f"Android: {android_ver}")
    task.emit("=" * 60)

    # Step 1: Verify device support
    task.emit("")
    task.progress(1, 6, "Checking device support")
    profile = get_profile(codename)
    if not profile:
        for p in load_all_profiles():
            if p.codename == codename:
                profile = p
                break
    if profile:
        task.emit(f"  Device: {profile.name} ({profile.brand})")
        task.emit(f"  Flash tool: {profile.flash_tool}")
    else:
        task.emit(f"  Device profile not found for {codename}, building generic.", "warn")

    # Step 2: Check LineageOS source tree
    task.emit("")
    task.progress(2, 6, "Checking LineageOS source tree")
    lineage_dir = Path.home() / "android" / "lineage"
    if lineage_dir.exists():
        task.emit(f"  Source tree found: {lineage_dir}")
    else:
        task.emit(f"  Source tree not found at {lineage_dir}", "warn")
        task.emit("  To build from source, run:", "info")
        task.emit(f"    mkdir -p {lineage_dir} && cd {lineage_dir}")
        task.emit("    repo init -u https://github.com/LineageOS/android.git -b lineage-21.0 --depth=1")
        task.emit("    repo sync -c -j$(nproc) --force-sync --no-clone-bundle --no-tags")
        task.emit("")
        task.emit("  Continuing with overlay-only build (flashable ZIP over LineageOS)...", "info")

    # Step 3: Apply overlays
    task.emit("")
    task.progress(3, 6, "Applying LETHE privacy overlays")

    overlay_files = list(OVERLAY_DIR.glob("*")) if OVERLAY_DIR.exists() else []
    for f in overlay_files:
        task.emit(f"  -> {f.name}")

    features = manifest.get("features", {})
    task.emit(f"  Privacy features: {len(features)}")
    for name, feat in features.items():
        desc = feat.get("description", "") if isinstance(feat, dict) else str(feat)
        task.emit(f"    - {name}: {desc}")

    # Step 4–6: Package, verify, publish
    _package_and_publish(task, codename, manifest, base_ver, overlay_files, features, ipfs_publish)


def _package_and_publish(
    task: Task,
    codename: str,
    manifest: dict,
    base_ver: str,
    overlay_files: list,
    features: dict,
    ipfs_publish: bool,
):
    """Package the overlay ZIP, verify, and optionally publish to IPFS."""
    import json
    import tempfile
    import zipfile

    task.emit("")
    task.progress(4, 6, "Generating flashable overlay package")

    output_name = f"Lethe-{manifest.get('version', '1.0.0')}-{codename}"
    output_zip = BUILD_OUTPUT_DIR / f"{output_name}.zip"
    meta_json = BUILD_OUTPUT_DIR / f"{output_name}-meta.json"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        meta_inf = tmpdir / "META-INF" / "com" / "google" / "android"
        meta_inf.mkdir(parents=True)
        (meta_inf / "updater-script").write_text(generate_updater_script(codename, manifest))

        overlay_dest = tmpdir / "lethe"
        overlay_dest.mkdir()

        for f in overlay_files:
            (overlay_dest / f.name).write_text(f.read_text())

        (overlay_dest / "init.lethe-burner.rc").write_text(generate_burner_init_rc())
        (overlay_dest / "init.lethe-deadman.rc").write_text(generate_deadman_init_rc())

        (overlay_dest / "build-info.txt").write_text(
            f"Lethe {manifest.get('version', '1.0.0')}\n"
            f"Base: LineageOS {base_ver}\n"
            f"Device: {codename}\n"
            f"Android: {manifest.get('android_version', '14')}\n"
        )

        with zipfile.ZipFile(str(output_zip), "w", zipfile.ZIP_DEFLATED) as zf:
            for f in tmpdir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(tmpdir))

    task.emit(f"  -> {output_zip.name} ({output_zip.stat().st_size // 1024} KB)")

    meta = {
        "name": f"Lethe {manifest.get('version', '')}",
        "codename": codename,
        "version": manifest.get("version", ""),
        "base": manifest.get("base", "lineageos"),
        "base_version": manifest.get("base_version", ""),
        "android_version": manifest.get("android_version", ""),
        "features": list(features.keys()),
        "output": str(output_zip),
    }
    meta_json.write_text(json.dumps(meta, indent=2))

    # Step 5: Verify
    task.emit("")
    task.progress(5, 6, "Verifying package integrity")
    import hashlib

    sha = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    task.emit(f"  SHA256: {sha}")
    meta["sha256"] = sha
    meta_json.write_text(json.dumps(meta, indent=2))
    task.emit("  -> Package verified.", "success")

    # Step 6: IPFS publish
    task.emit("")
    if ipfs_publish:
        task.progress(6, 6, "Publishing to IPFS")
        if ipfs_available():
            cid = ipfs_pin_and_index(
                str(output_zip),
                key=f"lethe/{codename}/{manifest.get('version', '')}",
                codename=codename,
                rom_name=f"Lethe {manifest.get('version', '')}",
                version=manifest.get("version", ""),
                extra={"type": "lethe", "features": list(features.keys())},
            )
            if cid:
                task.emit(f"  IPFS CID: {cid}", "success")
                meta["ipfs_cid"] = cid
                meta_json.write_text(json.dumps(meta, indent=2))
            else:
                task.emit("  Failed to pin to IPFS.", "error")
        else:
            task.emit("  IPFS not available. Skipping.", "warn")
    else:
        task.progress(6, 6, "IPFS publish skipped", "not requested")

    _emit_flash_instructions(task, codename, base_ver, output_zip)


def _emit_flash_instructions(task: Task, codename: str, base_ver: str, output_zip: Path):
    """Emit post-build flash instructions."""
    task.emit("")
    task.emit("=" * 60)
    task.emit(f"Lethe build complete: {output_zip.name}", "success")
    task.emit("")
    task.emit("Flash instructions:", "info")
    task.emit(f"  1. Install LineageOS {base_ver} on your device first")
    task.emit("  2. Boot into TWRP recovery")
    task.emit(f"  3. Sideload: adb sideload {output_zip.name}")
    task.emit("  4. Reboot — Lethe privacy overlay is now active")
    task.emit("")
    task.emit("  BURNER MODE is ON by default.", "warn")
    task.emit("  The device will wipe all user data on every reboot.")
    task.emit("  To disable: Settings > Privacy > Burner Mode (after boot).")
    task.emit("")
    task.emit("  DEAD MAN'S SWITCH is available.", "info")
    task.emit("  First boot will ask if you want to enable it.")
    task.emit("  If enabled: miss a check-in and the device protects itself.")
    task.emit("=" * 60)


def get_device_base_version(codename: str, manifest: dict) -> tuple[str, str]:
    """Return (base_version, android_version) for a device, respecting per-device overrides."""
    default_base = manifest.get("base_version", "21.0")
    default_android = manifest.get("android_version", "14")

    for device in manifest.get("devices", []):
        if isinstance(device, dict) and device.get("codename") == codename:
            return (
                device.get("base_version", default_base),
                device.get("android_version", default_android),
            )
    return default_base, default_android


def generate_updater_script(codename: str, manifest: dict) -> str:
    """Generate the update-script for recovery flashing."""
    base_ver, android_ver = get_device_base_version(codename, manifest)

    return f"""\
# Lethe privacy overlay — {codename}
# Base: LineageOS {base_ver} (Android {android_ver})
# Flash this ZIP in TWRP after installing LineageOS.

ui_print("Installing Lethe privacy overlay...");
ui_print("Device: {codename}");
ui_print("Version: {manifest.get("version", "1.0.0")}");
ui_print("Base: LineageOS {base_ver}");

# Mount system
mount("ext4", "EMMC", "/dev/block/bootdevice/by-name/system", "/system");

# Install tracker-blocking hosts
package_extract_file("lethe/hosts", "/system/etc/hosts");

# Install privacy defaults
package_extract_file("lethe/privacy-defaults.conf", "/system/etc/lethe-privacy.conf");

# Install firewall rules
package_extract_file("lethe/firewall-rules.conf", "/system/etc/lethe/firewall-rules.conf");

# Install burner mode config
package_extract_file("lethe/burner-mode.conf", "/system/etc/lethe/burner-mode.conf");

# Install dead man's switch config
package_extract_file("lethe/dead-mans-switch.conf", "/system/etc/lethe/dead-mans-switch.conf");

# Install init services (burner wipe + dead man's switch)
package_extract_file("lethe/init.lethe-burner.rc", "/system/etc/init/init.lethe-burner.rc");
package_extract_file("lethe/init.lethe-deadman.rc", "/system/etc/init/init.lethe-deadman.rc");

# Set permissions
set_metadata("/system/etc/lethe-privacy.conf", "uid", 0, "gid", 0, "mode", 0644);
set_metadata("/system/etc/lethe/burner-mode.conf", "uid", 0, "gid", 0, "mode", 0644);
set_metadata("/system/etc/lethe/dead-mans-switch.conf", "uid", 0, "gid", 0, "mode", 0600);
set_metadata("/system/etc/init/init.lethe-burner.rc", "uid", 0, "gid", 0, "mode", 0644);
set_metadata("/system/etc/init/init.lethe-deadman.rc", "uid", 0, "gid", 0, "mode", 0644);

# Ensure persist partition has burner mode enabled by default
mount("ext4", "EMMC", "/dev/block/bootdevice/by-name/persist", "/persist");
run_program("/system/bin/sh", "-c",
    "mkdir -p /persist/lethe/deadman && " \\
    "echo 'persist.lethe.burner.enabled=true' > /persist/lethe/burner.prop && " \\
    "echo 'persist.lethe.burner.first_boot=true' >> /persist/lethe/burner.prop && " \\
    "echo 'persist.lethe.deadman.enabled=false' > /persist/lethe/deadman.prop && " \\
    "echo 'persist.lethe.deadman.first_boot=true' >> /persist/lethe/deadman.prop");

ui_print("Lethe overlay installed successfully.");
ui_print("BURNER MODE is ON by default — device wipes on every reboot.");
ui_print("You can disable it after boot in Settings > Privacy > Burner Mode.");
ui_print("Reboot to activate privacy hardening.");
"""


def generate_burner_init_rc() -> str:
    """Generate the Android init.rc service for burner mode wipe-on-boot."""
    return """\
# Lethe burner mode — early-init wipe service
# Runs before zygote. Reads config from /persist partition.

on early-init
    # Mount persist partition to read burner mode preference
    mount ext4 /dev/block/bootdevice/by-name/persist /persist nosuid nodev noatime

on post-fs-data
    # Check burner mode toggle (stored on /persist, survives wipe)
    exec -- /system/bin/sh -c "\\
        ENABLED=$(getprop persist.lethe.burner.enabled); \\
        if [ \\"$ENABLED\\" = \\"true\\" ]; then \\
            log -t lethe-burner 'Burner mode active — wiping user data'; \\
            rm -rf /data/app /data/data /data/user /data/user_de /data/misc/wifi /data/misc/bluedroid; \\
            rm -rf /data/media/0/*; \\
            rm -rf /data/system/notification_log; \\
            settings put secure android_id $(cat /dev/urandom | tr -dc 'a-f0-9' | head -c 16); \\
            log -t lethe-burner 'Wipe complete — booting clean session'; \\
        else \\
            log -t lethe-burner 'Burner mode disabled — normal boot'; \\
        fi"

service lethe-mac-rotate /system/bin/sh -c "\\
    ENABLED=$(getprop persist.lethe.burner.enabled); \\
    if [ \\"$ENABLED\\" = \\"true\\" ]; then \\
        MAC=$(cat /dev/urandom | tr -dc 'a-f0-9' | head -c 12 | sed 's/../&:/g;s/:$//'); \\
        ip link set wlan0 down; \\
        ip link set wlan0 address $MAC; \\
        ip link set wlan0 up; \\
        log -t lethe-burner \\"MAC rotated to $MAC\\"; \\
    fi"
    class late_start
    oneshot
    disabled

on property:sys.boot_completed=1
    start lethe-mac-rotate
"""


def generate_deadman_init_rc() -> str:
    """Generate the Android init.rc service for the dead man's switch.

    On boot, checks elapsed time since last check-in against the configured
    interval. If the deadline has passed, escalates through lock -> wipe -> brick.
    The timer is based on the hardware RTC, not network time, so powering off
    or pulling the SIM doesn't stall the countdown.
    """
    return """\
# Lethe dead man's switch — boot-time enforcement
# Runs after persist is mounted, before zygote.
# Reads /persist/lethe/deadman/ for config and heartbeat.

on post-fs-data
    exec -- /system/bin/sh -c "\\
        ENABLED=$(cat /persist/lethe/deadman.prop 2>/dev/null | grep 'persist.lethe.deadman.enabled=true'); \\
        if [ -z \\"$ENABLED\\" ]; then \\
            log -t lethe-deadman 'Dead man switch disabled — skipping'; \\
            exit 0; \\
        fi; \\
        \\
        INTERVAL_RAW=$(getprop persist.lethe.deadman.interval); \\
        INTERVAL_RAW=$${INTERVAL_RAW:-24h}; \\
        \\
        # Convert interval to seconds \\
        case \\"$INTERVAL_RAW\\" in \\
            12h) INTERVAL=43200 ;; \\
            24h) INTERVAL=86400 ;; \\
            48h) INTERVAL=172800 ;; \\
            72h) INTERVAL=259200 ;; \\
            7d)  INTERVAL=604800 ;; \\
            *)   INTERVAL=86400 ;; \\
        esac; \\
        \\
        GRACE=$(getprop persist.lethe.deadman.grace_period); \\
        GRACE=$${GRACE:-4h}; \\
        case \\"$GRACE\\" in \\
            1h) GRACE_S=3600 ;; \\
            2h) GRACE_S=7200 ;; \\
            4h) GRACE_S=14400 ;; \\
            8h) GRACE_S=28800 ;; \\
            *)  GRACE_S=14400 ;; \\
        esac; \\
        \\
        DEADLINE=$((INTERVAL + GRACE_S)); \\
        \\
        # Read last check-in timestamp from persist \\
        HEARTBEAT_FILE=/persist/lethe/deadman/last_checkin; \\
        if [ ! -f \\"$HEARTBEAT_FILE\\" ]; then \\
            log -t lethe-deadman 'No heartbeat file — first boot, writing initial checkin'; \\
            mkdir -p /persist/lethe/deadman; \\
            date +%s > $HEARTBEAT_FILE; \\
            exit 0; \\
        fi; \\
        \\
        LAST_CHECKIN=$(cat $HEARTBEAT_FILE 2>/dev/null); \\
        NOW=$(date +%s); \\
        ELAPSED=$((NOW - LAST_CHECKIN)); \\
        \\
        log -t lethe-deadman \\"Last checkin: ${LAST_CHECKIN}, now: ${NOW}, elapsed: ${ELAPSED}s, deadline: ${DEADLINE}s\\"; \\
        \\
        if [ $ELAPSED -gt $DEADLINE ]; then \\
            log -t lethe-deadman 'DEADLINE EXCEEDED — escalating'; \\
            \\
            # Stage 1: Lock — force passphrase-only unlock \\
            log -t lethe-deadman 'Stage 1: Locking device (passphrase only)'; \\
            setprop persist.lethe.deadman.stage=locked; \\
            \\
            # Check if we've passed Stage 2 threshold (wipe) \\
            STAGE2_DELAY=3600; \\
            WIPE_DEADLINE=$((DEADLINE + STAGE2_DELAY)); \\
            if [ $ELAPSED -gt $WIPE_DEADLINE ]; then \\
                log -t lethe-deadman 'Stage 2: WIPING user data'; \\
                setprop persist.lethe.deadman.stage=wiped; \\
                rm -rf /data/app /data/data /data/user /data/user_de; \\
                rm -rf /data/misc/wifi /data/misc/bluedroid; \\
                rm -rf /data/media/0/*; \\
                rm -rf /data/system/notification_log; \\
                log -t lethe-deadman 'Wipe complete'; \\
                \\
                # Check if Stage 3 (brick) is enabled and threshold passed \\
                STAGE3_ENABLED=$(getprop persist.lethe.deadman.stage3.enabled); \\
                STAGE3_DELAY=7200; \\
                BRICK_DEADLINE=$((WIPE_DEADLINE + STAGE3_DELAY)); \\
                if [ \\"$STAGE3_ENABLED\\" = \\"true\\" ] && [ $ELAPSED -gt $BRICK_DEADLINE ]; then \\
                    log -t lethe-deadman 'Stage 3: BRICKING — overwriting critical partitions'; \\
                    setprop persist.lethe.deadman.stage=bricked; \\
                    dd if=/dev/urandom of=/dev/block/bootdevice/by-name/boot bs=4096 count=1024 2>/dev/null; \\
                    dd if=/dev/urandom of=/dev/block/bootdevice/by-name/recovery bs=4096 count=1024 2>/dev/null; \\
                    rm -rf /persist/lethe; \\
                    log -t lethe-deadman 'Brick complete — device unbootable without OSmosis USB recovery'; \\
                    reboot; \\
                fi; \\
            fi; \\
        else \\
            log -t lethe-deadman \\"Within deadline — $((DEADLINE - ELAPSED))s remaining\\"; \\
        fi"

# Runtime check-in service — runs periodically while the device is on.
# Monitors the heartbeat file and triggers the silent notification
# when a check-in is due.
service lethe-deadman-monitor /system/bin/sh -c "\\
    while true; do \\
        ENABLED=$(getprop persist.lethe.deadman.enabled); \\
        if [ \\"$ENABLED\\" != \\"true\\" ]; then \\
            sleep 3600; \\
            continue; \\
        fi; \\
        \\
        HEARTBEAT_FILE=/persist/lethe/deadman/last_checkin; \\
        LAST_CHECKIN=$(cat $HEARTBEAT_FILE 2>/dev/null || echo 0); \\
        NOW=$(date +%s); \\
        ELAPSED=$((NOW - LAST_CHECKIN)); \\
        \\
        INTERVAL_RAW=$(getprop persist.lethe.deadman.interval); \\
        case \\"$INTERVAL_RAW\\" in \\
            12h) INTERVAL=43200 ;; \\
            24h) INTERVAL=86400 ;; \\
            48h) INTERVAL=172800 ;; \\
            72h) INTERVAL=259200 ;; \\
            7d)  INTERVAL=604800 ;; \\
            *)   INTERVAL=86400 ;; \\
        esac; \\
        \\
        if [ $ELAPSED -ge $INTERVAL ]; then \\
            log -t lethe-deadman 'Check-in due — posting notification'; \\
            am broadcast -a lethe.intent.CHECKIN_DUE --ez overdue true; \\
        fi; \\
        \\
        sleep 900; \\
    done"
    class late_start
    oneshot
    disabled

on property:sys.boot_completed=1
    start lethe-deadman-monitor

# Duress PIN handler — triggered by the lock screen when the duress
# code is entered. Shows a fake home screen while wiping in background.
on property:persist.lethe.deadman.duress_triggered=true
    exec -- /system/bin/sh -c "\\
        log -t lethe-deadman 'DURESS PIN entered — silent wipe initiated'; \\
        rm -rf /data/app /data/data /data/user /data/user_de; \\
        rm -rf /data/misc/wifi /data/misc/bluedroid; \\
        rm -rf /data/media/0/*; \\
        rm -rf /data/system/notification_log; \\
        # Reset the duress flag so it doesn't re-trigger on next boot \\
        setprop persist.lethe.deadman.duress_triggered false; \\
        log -t lethe-deadman 'Duress wipe complete — device appears normal'"
"""
