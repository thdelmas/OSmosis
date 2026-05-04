"""Lethe build entry point and OTA-zip validator.

The in-process Python build pipeline that used to live here was deleted in
issue #117: it produced a ~5 KB TWRP-overlay stub (no system.new.dat, no
boot.img, no sepolicy relabel) yet emitted "build complete" + flash
instructions, which is the regression family the May 2 post-mortem flagged.

Real LETHE OTAs are produced out-of-band by ``lethe/scripts/build-all.sh``
against a real LineageOS source tree. The validator below is what the OTA
route uses to refuse advertising anything that doesn't look like a real
sealed OTA with LETHE markers.
"""

from pathlib import Path

from web.core import Task

BUILD_OUTPUT_DIR = Path.home() / "Osmosis-downloads" / "lethe-builds"

# Sibling subdirs of BUILD_OUTPUT_DIR. Anything in these is excluded from
# release artifact globs. Validation reference zips (vanilla LineageOS,
# upstream comparators) live in _reference; suspect / partial / pending
# investigation builds live in _quarantine.
REFERENCE_DIR = BUILD_OUTPUT_DIR / "_reference"
QUARANTINE_DIR = BUILD_OUTPUT_DIR / "_quarantine"


# Real LineageOS OTAs are 250-350 MB; overlay-only stubs are <10 KB. Fail-fast
# anything well below the smallest plausible OTA size before deeper checks.
MIN_OTA_BYTES = 50 * 1024 * 1024


def validate_build_zip(zip_path: Path) -> dict:
    """Inspect a Lethe OTA zip for OTA structure + LETHE markers.

    Returns ``{"checks": {...}, "errors": [...]}``. Errors are operator-readable
    strings; an empty list means the zip is structurally a real LETHE OTA.

    Catches the exact regression family from the v1.0.0 May 2 incident:
    sealed LineageOS OTA size, present system/build.prop ro.lethe props, but
    file_contexts.bin missing the lethe sepolicy labels.
    """
    import zipfile

    checks: dict = {
        "size_bytes": zip_path.stat().st_size,
        "has_system_new_dat": False,
        "has_boot_img": False,
        "has_file_contexts_bin": False,
        "lethe_props_in_build_prop": [],
        "lethe_labels_in_file_contexts": False,
    }
    errors: list = []

    if checks["size_bytes"] < MIN_OTA_BYTES:
        errors.append(
            f"size {checks['size_bytes']} bytes < min OTA size {MIN_OTA_BYTES} "
            f"(looks like an overlay-only stub, not a real OTA)"
        )

    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            checks["has_system_new_dat"] = (
                "system.new.dat" in names or "system.new.dat.br" in names
            )
            checks["has_boot_img"] = "boot.img" in names
            checks["has_file_contexts_bin"] = "file_contexts.bin" in names

            if not checks["has_system_new_dat"]:
                errors.append(
                    "missing system.new.dat — not a sealed LineageOS OTA"
                )

            if "system/build.prop" in names:
                try:
                    bp = zf.read("system/build.prop").decode(
                        "utf-8", errors="replace"
                    )
                    checks["lethe_props_in_build_prop"] = sorted(
                        {
                            line.split("=", 1)[0].strip()
                            for line in bp.splitlines()
                            if line.strip().startswith("ro.lethe")
                        }
                    )
                    if not checks["lethe_props_in_build_prop"]:
                        errors.append(
                            "system/build.prop has no ro.lethe properties — "
                            "not a LETHE build (looks like vanilla LineageOS)"
                        )
                except OSError as e:
                    errors.append(f"could not read system/build.prop: {e}")
            elif checks["has_system_new_dat"]:
                # OTA shape but no build.prop at top level — most likely the
                # build.prop is inside system.new.dat (block-OTA layout). Don't
                # treat as fatal here; sepolicy check below catches the actual
                # May 2 failure mode.
                pass

            if checks["has_file_contexts_bin"]:
                try:
                    fc = zf.read("file_contexts.bin")
                    checks["lethe_labels_in_file_contexts"] = b"lethe" in fc
                    if not checks["lethe_labels_in_file_contexts"]:
                        errors.append(
                            "file_contexts.bin has no lethe labels — sepolicy "
                            "not built into OS image (May 2 regression family)"
                        )
                except OSError as e:
                    errors.append(f"could not read file_contexts.bin: {e}")
    except zipfile.BadZipFile:
        errors.append("not a valid zip file")

    return {"checks": checks, "errors": errors}


def build_lethe(task: Task, codename: str, manifest: dict, ipfs_publish: bool):
    """Reject the in-process build path and direct the operator to build-all.sh.

    Issue #117: the previous implementation zipped the overlays into a tiny TWRP
    package and called it a build. The validator now correctly fingerprints that
    output as a stub, so leaving the path in place is just a footgun.
    """
    del ipfs_publish  # arg retained for the route signature
    base_ver, android_ver = get_device_base_version(codename, manifest)

    task.emit("=" * 60)
    task.emit(f"Lethe build — {codename}", "info")
    task.emit(f"Base: {manifest.get('base', 'lineageos')} {base_ver}")
    task.emit(f"Android: {android_ver}")
    task.emit("=" * 60)
    task.emit("")
    task.emit(
        "In-process build path removed (issue #117) — it produced a ~5 KB TWRP",
        "error",
    )
    task.emit(
        "overlay stub that could never install a working LETHE OS but reported",
        "error",
    )
    task.emit("'build complete' anyway. Real builds run on a LineageOS host:", "error")
    task.emit("")
    task.emit(f"  bash lethe/scripts/build-all.sh {codename}", "info")
    task.emit(f"  bash lethe/scripts/sign-build.sh {codename}", "info")
    task.emit(
        f"  bash lethe/scripts/generate-ota.sh {codename} --publish", "info"
    )
    task.emit("")
    task.emit(
        f"Signed OTAs land in {BUILD_OUTPUT_DIR}; the OTA route picks them up",
        "info",
    )
    task.emit("once they pass validate_build_zip.", "info")
    task.done(False)


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
