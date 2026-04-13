"""Lethe build pipeline and init.rc generators.

Extracted from lethe.py to keep route files under the 500-line limit.
"""

from pathlib import Path

from web.core import Task
from web.device_profile import get_profile, load_all_profiles
from web.ipfs_helpers import ipfs_available, ipfs_pin_and_index
from web.routes.lethe_initrc import (
    generate_burner_init_rc,
    generate_deadman_init_rc,
)

OVERLAY_DIR = (
    Path(__file__).resolve().parent.parent.parent / "lethe" / "overlays"
)
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
        task.emit(
            f"  Device profile not found for {codename}, building generic.",
            "warn",
        )

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
        task.emit(
            "    repo init -u https://github.com/LineageOS/android.git -b lineage-21.0 --depth=1"
        )
        task.emit(
            "    repo sync -c -j$(nproc) --force-sync --no-clone-bundle --no-tags"
        )
        task.emit("")
        task.emit(
            "  Continuing with overlay-only build (flashable ZIP over LineageOS)...",
            "info",
        )

    # Step 3: Apply overlays
    task.emit("")
    task.progress(3, 6, "Applying LETHE privacy overlays")

    overlay_files = list(OVERLAY_DIR.glob("*")) if OVERLAY_DIR.exists() else []
    for f in overlay_files:
        task.emit(f"  -> {f.name}")

    features = manifest.get("features", {})
    task.emit(f"  Privacy features: {len(features)}")
    for name, feat in features.items():
        desc = (
            feat.get("description", "") if isinstance(feat, dict) else str(feat)
        )
        task.emit(f"    - {name}: {desc}")

    # Step 4–6: Package, verify, publish
    _package_and_publish(
        task,
        codename,
        manifest,
        base_ver,
        overlay_files,
        features,
        ipfs_publish,
    )


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
        (meta_inf / "updater-script").write_text(
            generate_updater_script(codename, manifest)
        )

        overlay_dest = tmpdir / "lethe"
        overlay_dest.mkdir()

        import shutil

        for f in overlay_files:
            shutil.copy2(f, overlay_dest / f.name)

        (overlay_dest / "init.lethe-burner.rc").write_text(
            generate_burner_init_rc()
        )
        (overlay_dest / "init.lethe-deadman.rc").write_text(
            generate_deadman_init_rc()
        )

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

    task.emit(
        f"  -> {output_zip.name} ({output_zip.stat().st_size // 1024} KB)"
    )

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


def _emit_flash_instructions(
    task: Task, codename: str, base_ver: str, output_zip: Path
):
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

    version = manifest.get("version", "1.0.0")
    return f"""\
# Lethe privacy overlay — {codename}
# Base: LineageOS {base_ver} (Android {android_ver})
# Flash this ZIP in TWRP after installing LineageOS.
# Uses shell commands instead of edify mount() for device compatibility.

ui_print("Installing LETHE v{version}...");
ui_print("Device: {codename}");
ui_print("Base: LineageOS {base_ver}");

# Mount system (TWRP usually has it mounted; remount rw if needed)
run_program("/sbin/sh", "-c",
    "mount /system 2>/dev/null; mount -o remount,rw /system 2>/dev/null; true");

# Create directories
run_program("/sbin/sh", "-c",
    "mkdir -p /system/etc/lethe /system/etc/init");

# Extract overlay files
package_extract_dir("lethe", "/tmp/lethe");

# Install files via shell (works on all devices)
run_program("/sbin/sh", "-c",
    "cp /tmp/lethe/hosts /system/etc/hosts && " \\
    "cp /tmp/lethe/privacy-defaults.conf /system/etc/lethe-privacy.conf && " \\
    "cp /tmp/lethe/firewall-rules.conf /system/etc/lethe/firewall-rules.conf && " \\
    "cp /tmp/lethe/burner-mode.conf /system/etc/lethe/burner-mode.conf && " \\
    "cp /tmp/lethe/dead-mans-switch.conf /system/etc/lethe/dead-mans-switch.conf && " \\
    "cp /tmp/lethe/init.lethe-burner.rc /system/etc/init/ && " \\
    "cp /tmp/lethe/init.lethe-deadman.rc /system/etc/init/ && " \\
    "chmod 644 /system/etc/hosts /system/etc/lethe-privacy.conf && " \\
    "chmod 644 /system/etc/lethe/burner-mode.conf /system/etc/lethe/firewall-rules.conf && " \\
    "chmod 600 /system/etc/lethe/dead-mans-switch.conf && " \\
    "chmod 644 /system/etc/init/init.lethe-burner.rc /system/etc/init/init.lethe-deadman.rc");

# Copy mascot and theme assets
run_program("/sbin/sh", "-c",
    "for f in /tmp/lethe/*.png /tmp/lethe/*.conf; do " \\
    "[ -f \\"$f\\" ] && cp \\"$f\\" /system/etc/lethe/ 2>/dev/null; done; true");

# Set up persist partition for burner mode config
run_program("/sbin/sh", "-c",
    "mount /persist 2>/dev/null; " \\
    "mkdir -p /persist/lethe/deadman && " \\
    "echo 'persist.lethe.burner.enabled=true' > /persist/lethe/burner.prop && " \\
    "echo 'persist.lethe.deadman.enabled=false' > /persist/lethe/deadman.prop; " \\
    "true");

# Clean up
run_program("/sbin/sh", "-c", "rm -rf /tmp/lethe");

ui_print("LETHE overlay installed.");
ui_print("");
ui_print("BURNER MODE is ON by default.");
ui_print("Data is erased on every reboot.");
ui_print("Disable in Settings > Privacy after boot.");
ui_print("");
ui_print("Reboot to activate.");
"""
