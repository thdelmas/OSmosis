#!/usr/bin/env bash
# recover-t0lte.sh — Reflash stock Samsung firmware to a Galaxy Note II LTE
# (GT-N7105 / codename t0lte) via Heimdall. Use this when the device bootloops
# even after a vanilla LineageOS reflash and you've already ruled out the OTA
# layer — i.e. the boot/system/modem/bootloader regions might be damaged at a
# layer below what TWRP can format.
#
# Modeled on recover-sm-t805.sh. Heimdall's partition flag names come from
# the device's PIT file; if the firmware revision you downloaded doesn't match
# the partitions referenced below, run `sudo heimdall print-pit` first to see
# the live layout and adjust.
#
# Pre-reqs:
#   - heimdall (apt install heimdall-flash)
#   - SM-N7105 stock firmware tarball in $FW_ZIP (default: first match of
#     ~/Downloads/*N7105*.zip — samfw.com naming pattern). Pick a CSC region
#     matching the device.
#   - Device in Download Mode: Power + Home + Volume Down, then Volume Up to
#     confirm. Plug USB after the warning screen appears.

set -euo pipefail

FW_ZIP="${FW_ZIP:-}"
WORK_DIR="${WORK_DIR:-$HOME/Downloads/SM-N7105-firmware}"

echo "== GT-N7105 (t0lte) stock firmware recovery =="

if [[ -z "$FW_ZIP" ]]; then
    # No explicit FW_ZIP — auto-pick the most recent matching zip in ~/Downloads
    FW_ZIP="$(ls -t "$HOME"/Downloads/*N7105*.zip 2>/dev/null | head -1 || true)"
fi

if [[ -z "$FW_ZIP" || ! -f "$FW_ZIP" ]]; then
    echo "ERROR: No stock firmware zip found." >&2
    echo "  Drop a SAMFW.COM_SM-N7105_*_fac.zip (or similar) into ~/Downloads/" >&2
    echo "  then re-run, or set FW_ZIP=/path/to/firmware.zip" >&2
    exit 1
fi

if ! command -v heimdall >/dev/null 2>&1; then
    echo "ERROR: heimdall not found. Install with:" >&2
    echo "  sudo apt update && sudo apt install heimdall-flash" >&2
    exit 1
fi

echo "Using firmware zip: $FW_ZIP"
echo "Working directory:  $WORK_DIR"
mkdir -p "$WORK_DIR"

echo
echo "== Extracting main firmware zip =="
unzip -o "$FW_ZIP" -d "$WORK_DIR"

cd "$WORK_DIR"

echo
echo "== Extracting BL/AP/CP/CSC tar.md5 files =="
# Each tar contains a different partition family. Some firmware revisions
# don't ship a BL_ tarball (bootloader bundled into AP_ instead) — tolerate.
for prefix in BL AP CP CSC; do
    set +e
    tarball=$(ls "$prefix"_*.tar.md5 2>/dev/null | head -1)
    set -e
    if [[ -n "$tarball" ]]; then
        echo "  -> $tarball"
        tar -xvf "$tarball"
    else
        echo "  (no $prefix_*.tar.md5; skipping)"
    fi
done

echo
echo "Files in firmware directory:"
ls

# Sanity-check the partition images we plan to flash. Some revisions ship
# images with .ext4 suffix instead of .img — handle both. .lz4-compressed
# images need to be decompressed first (some Note II revisions ship .lz4).
declare -A IMG=(
    [BOOT]=""        # boot.img
    [RECOVERY]=""    # recovery.img
    [SYSTEM]=""      # system.img / system.img.ext4
    [CACHE]=""       # cache.img / cache.img.ext4
    [HIDDEN]=""      # hidden.img / hidden.img.ext4
    [USERDATA]=""    # userdata.img / userdata.img.ext4 (often absent — firmware preserves user data; wipe via TWRP after)
    [RADIO]=""       # modem.bin
    [BOOTLOADER]=""  # sboot.bin (BL_ tarball; not always present)
    [TZSW]=""        # tz.img (TrustZone software — *critical* for Exynos boot; bundled in BL)
    [PARAM]=""       # param.bin (build params + LCD calibration; bundled in BL)
    [TOMBSTONES]=""  # tombstones.img (native-crash dump partition; bundled in AP)
)

resolve() {
    # First arg = partition (BOOT etc), remaining = candidate filenames.
    # Picks the first that exists (after .lz4 decompression if needed).
    local part=$1; shift
    for cand in "$@"; do
        if [[ -f "$cand.lz4" && ! -f "$cand" ]]; then
            echo "  -> decompress $cand.lz4"
            lz4 -d "$cand.lz4" "$cand"
        fi
        if [[ -f "$cand" ]]; then
            IMG[$part]="$cand"
            return 0
        fi
    done
}

resolve BOOT       boot.img
resolve RECOVERY   recovery.img
resolve SYSTEM     system.img.ext4 system.img
resolve CACHE      cache.img.ext4 cache.img
resolve HIDDEN     hidden.img.ext4 hidden.img
resolve USERDATA   userdata.img.ext4 userdata.img
resolve BOOTLOADER sboot.bin
resolve TZSW       tz.img
resolve PARAM      param.bin
resolve TOMBSTONES tombstones.img
resolve RADIO      modem.bin

echo
echo "== Partition image map =="
for part in BOOTLOADER PARAM TZSW BOOT RECOVERY SYSTEM CACHE HIDDEN USERDATA TOMBSTONES RADIO; do
    if [[ -n "${IMG[$part]}" ]]; then
        printf "  %-10s %s\n" "$part" "${IMG[$part]}"
    else
        printf "  %-10s (missing — will skip)\n" "$part"
    fi
done

# Build the heimdall flag list from whatever resolved. Ordering follows the
# Note II PIT layout (BOOTLOADER → PARAM → TZSW → kernel/system → RADIO).
heimdall_args=()
for part in BOOTLOADER PARAM TZSW BOOT RECOVERY SYSTEM CACHE HIDDEN USERDATA TOMBSTONES RADIO; do
    if [[ -n "${IMG[$part]}" ]]; then
        heimdall_args+=("--$part" "${IMG[$part]}")
    fi
done

if [[ ${#heimdall_args[@]} -eq 0 ]]; then
    echo "ERROR: No flashable partition images found in $WORK_DIR." >&2
    exit 2
fi

echo
echo "== IMPORTANT =="
echo "1) Put the phone into DOWNLOAD MODE now:"
echo "   Power + Home + Volume Down, then Volume Up to confirm"
echo "2) Connect it to this computer via USB"
echo
read -rp "When the phone is in Download Mode and plugged in, press Enter to continue..."

echo
echo "== Checking Heimdall device detection (with sudo) =="
sudo heimdall detect

echo
echo "Optional: dump the live PIT to verify partition names match. Skip with N."
read -rp "Print PIT now? [y/N] " print_pit
if [[ "${print_pit,,}" == "y" ]]; then
    # Capture full output to a tmpfile first — `heimdall print-pit | head` under
    # `set -euo pipefail` aborts the script on SIGPIPE when head closes early.
    pit_dump="$(mktemp -t t0lte-pit.XXXXXX)"
    if ! sudo heimdall print-pit > "$pit_dump" 2>&1; then
        echo "WARNING: heimdall print-pit failed; continuing with the partition map already resolved." >&2
    fi
    head -120 "$pit_dump" || true
    echo "(full PIT dump at $pit_dump)"
fi

echo
echo "If 'Device detected' appeared above, we will now flash the full stock firmware."
echo "DO NOT disconnect the USB cable during flashing."
echo
echo "Flash command will be:"
echo "  sudo heimdall flash ${heimdall_args[*]}"
echo
read -rp "Press Enter to start flashing (or Ctrl+C to abort)..."

echo
echo "== Flashing stock firmware to GT-N7105 =="
sudo heimdall flash "${heimdall_args[@]}"

echo
echo "== Flash complete (if no errors were shown) =="
echo "If the phone doesn't reboot automatically:"
echo "  - Hold Power + Home + Volume Down until it turns off"
echo "  - Then immediately press Power + Home + Volume Up to enter STOCK RECOVERY"
echo
echo "In stock recovery:"
echo "  - Wipe data/factory reset"
echo "  - Wipe cache partition"
echo "  - Reboot system now"
echo
echo "If, after this, the phone still bootloops on the stock TouchWiz boot"
echo "animation, the eMMC or battery is the failure (hardware), and a vanilla"
echo "Lethe v1.0.x build still won't validate against this handset. Either swap"
echo "the battery (Note II batteries are user-replaceable) or use a different"
echo "t0lte test device."
