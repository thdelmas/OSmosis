#!/usr/bin/env bash
#
# flash-wizard.sh
# Interactive helper for flashing Samsung devices (Heimdall) and
# installing custom ROM / GApps via adb sideload.
#
# It does NOT hard‑code any particular model. You can:
# - Provide paths manually (firmware ZIP, recovery .img, ROM / GApps zips)
# - Or define device presets and download URLs in devices.cfg
#
# The script guides you through:
# - Required physical steps (Download Mode, Recovery, ADB sideload)
# - Confirming commands before they run
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/devices.cfg"
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
  esac
done

########################################
# Session logging
########################################

LOG_DIR="$HOME/.flashwizard/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/session-$(date +%Y%m%d-%H%M%S).log"

# Duplicate all stdout and stderr to the log file while keeping terminal output.
exec > >(tee -a "$LOG_FILE") 2>&1

echo "FlashWizard session started: $(date)"
echo "Log file: $LOG_FILE"
echo

if $DRY_RUN; then
  echo "[DRY-RUN] Mode enabled — no destructive commands will be executed."
  echo
fi

# Wrapper: prints the command, and skips execution in dry-run mode.
run_cmd() {
  echo "  >> $*"
  if $DRY_RUN; then
    echo "  [DRY-RUN] Skipped."
    return 0
  fi
  "$@"
}

########################################
# Utility helpers
########################################

prompt() {
  local msg=$1
  read -r -p "$msg" REPLY
  printf '%s\n' "$REPLY"
}

confirm() {
  local msg=$1
  read -r -p "$msg [y/N]: " REPLY
  case "$REPLY" in
    [Yy]*) return 0 ;;
    *)     return 1 ;;
  esac
}

require_cmd() {
  local cmd=$1
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: '$cmd' is not installed or not in PATH."
    if [[ "$cmd" == "heimdall" ]]; then
      echo "Install with:  sudo apt update && sudo apt install heimdall-flash"
    elif [[ "$cmd" == "adb" ]]; then
      echo "Install with:  sudo apt update && sudo apt install adb"
    fi
    exit 1
  fi
}

wget_retry() {
  local max_attempts=3
  local attempt=1
  while (( attempt <= max_attempts )); do
    echo "  Download attempt $attempt/$max_attempts..."
    if wget --tries=1 --timeout=30 "$@"; then
      return 0
    fi
    echo "  WARNING: Download failed (attempt $attempt/$max_attempts)."
    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      echo "  Retrying in 3 seconds..."
      sleep 3
    fi
  done
  echo "  ERROR: Download failed after $max_attempts attempts."
  return 1
}

verify_sha256() {
  local file=$1
  local expected=${2:-}  # optional: expected hash (empty = just display)

  if [[ ! -f "$file" ]]; then
    echo "WARNING: Cannot verify checksum — file not found: $file"
    return 1
  fi

  local actual
  actual=$(sha256sum "$file" | awk '{print $1}')

  if [[ -n "$expected" ]]; then
    if [[ "$actual" == "$expected" ]]; then
      echo "SHA256 OK: $actual"
      return 0
    else
      echo "SHA256 MISMATCH!"
      echo "  Expected: $expected"
      echo "  Got:      $actual"
      return 1
    fi
  else
    echo "SHA256: $actual"
    return 0
  fi
}

########################################
# Heimdall / Samsung helpers
########################################

check_heimdall_device() {
  echo
  echo "== Checking Heimdall device detection (with sudo) =="
  local attempt=1
  local max_attempts=3
  while (( attempt <= max_attempts )); do
    if run_cmd sudo heimdall detect; then
      return 0
    fi
    echo "WARNING: Device not detected (attempt $attempt/$max_attempts)."
    echo "Check that the device is in DOWNLOAD MODE and the USB cable is connected."
    echo "For Samsung: Power + Home + Volume Down, then Volume Up to confirm."
    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      prompt "Fix the connection and press Enter to retry..."
    fi
  done
  echo "ERROR: Heimdall could not detect a device after $max_attempts attempts."
  exit 1
}

flash_stock_firmware() {
  echo "== Stock firmware restore (Samsung / Heimdall) =="
  echo
  echo "This expects a Samsung firmware ZIP containing BL/AP/CP/CSC *.tar.md5 files."
  echo "Example: SAMFW.COM_SM-XXXX_... .zip or SamMobile/SamFrew firmware."
  echo

  local default_fw_zip="$HOME/Downloads"
  echo "Enter path to firmware ZIP (or leave empty to browse $default_fw_zip):"
  read -r FW_ZIP

  if [[ -z "$FW_ZIP" ]]; then
    echo "Listing *.zip in $default_fw_zip:"
    ls -1 "$default_fw_zip"/*.zip 2>/dev/null || true
    FW_ZIP=$(prompt "Type the full path to the firmware ZIP: ")
  fi

  if [[ ! -f "$FW_ZIP" ]]; then
    echo "ERROR: Firmware zip not found at: $FW_ZIP"
    exit 1
  fi

  echo
  verify_sha256 "$FW_ZIP"

  local base
  base=$(basename "$FW_ZIP")
  local WORK_DIR="$HOME/Downloads/${base%.zip}-unpacked"

  echo
  echo "Using firmware zip: $FW_ZIP"
  echo "Working directory:  $WORK_DIR"
  mkdir -p "$WORK_DIR"

  echo
  echo "== Extracting main firmware zip =="
  unzip -o "$FW_ZIP" -d "$WORK_DIR"

  cd "$WORK_DIR"

  echo
  echo "== Extracting BL/AP/CP/CSC tar.md5 files (if present) =="
  shopt -s nullglob
  for part in BL_*.tar.md5 AP_*.tar.md5 CP_*.tar.md5 CSC_*.tar.md5; do
    if [[ -f "$part" ]]; then
      echo "Extracting $part"
      tar -xvf "$part"
    fi
  done
  shopt -u nullglob

  # Decompress any .lz4 files (Android 12+ firmware often ships lz4-compressed images)
  shopt -s nullglob
  local lz4_files=(*.lz4)
  shopt -u nullglob
  if (( ${#lz4_files[@]} > 0 )); then
    if command -v lz4 >/dev/null 2>&1; then
      echo
      echo "== Decompressing .lz4 files =="
      for lz4f in "${lz4_files[@]}"; do
        echo "Decompressing $lz4f"
        lz4 -d -f "$lz4f" "${lz4f%.lz4}"
      done
    else
      echo
      echo "WARNING: .lz4 files found but 'lz4' command not available."
      echo "Install with:  sudo apt install lz4"
      echo "Continuing without decompression — Heimdall cannot flash .lz4 directly."
    fi
  fi

  echo
  echo "Files in firmware directory:"
  ls

  # Try to detect common image filenames.
  local BOOT="" RECOVERY="" SYSTEM="" MODEM="" CACHE="" HIDDEN="" USERDATA=""
  local SUPER="" VBMETA="" VENDOR="" PRODUCT="" ODM=""

  [[ -f boot.img ]] && BOOT="boot.img"
  [[ -f recovery.img ]] && RECOVERY="recovery.img"
  # Prefer plain system.img; fall back to first matching system*.img*
  if [[ -f system.img ]]; then
    SYSTEM="system.img"
  else
    SYSTEM=$(ls system*.img* 2>/dev/null | head -n 1 || true)
  fi
  [[ -f modem.bin ]] && MODEM="modem.bin"
  [[ -f NON-HLOS.bin ]] && MODEM=${MODEM:-"NON-HLOS.bin"}
  if [[ -f cache.img ]]; then
    CACHE="cache.img"
  else
    CACHE=$(ls cache*.img* 2>/dev/null | head -n 1 || true)
  fi
  if [[ -f hidden.img ]]; then
    HIDDEN="hidden.img"
  else
    HIDDEN=$(ls hidden*.img* 2>/dev/null | head -n 1 || true)
  fi
  if [[ -f userdata.img ]]; then
    USERDATA="userdata.img"
  else
    USERDATA=$(ls user*.img* 2>/dev/null | head -n 1 || true)
  fi

  # Android 12+ dynamic partition images
  [[ -f super.img ]] && SUPER="super.img"
  [[ -f vbmeta.img ]] && VBMETA="vbmeta.img"
  [[ -f vendor.img ]] && VENDOR="vendor.img"
  [[ -f product.img ]] && PRODUCT="product.img"
  [[ -f odm.img ]] && ODM="odm.img"

  # Detect firmware type
  local FW_TYPE="legacy"
  if [[ -n "$SUPER" ]]; then
    FW_TYPE="dynamic"
    echo
    echo "NOTE: super.img detected — this is an Android 12+ firmware with dynamic partitions."
  fi

  echo
  echo "Detected images (empty means not found):"
  echo "  BOOT:     ${BOOT:-<none>}"
  echo "  RECOVERY: ${RECOVERY:-<none>}"
  echo "  SYSTEM:   ${SYSTEM:-<none>}"
  echo "  MODEM:    ${MODEM:-<none>}"
  echo "  CACHE:    ${CACHE:-<none>}"
  echo "  HIDDEN:   ${HIDDEN:-<none>}"
  echo "  USERDATA: ${USERDATA:-<none>}"
  if [[ "$FW_TYPE" == "dynamic" ]]; then
    echo "  SUPER:    ${SUPER:-<none>}"
    echo "  VBMETA:   ${VBMETA:-<none>}"
    echo "  VENDOR:   ${VENDOR:-<none>}"
    echo "  PRODUCT:  ${PRODUCT:-<none>}"
    echo "  ODM:      ${ODM:-<none>}"
  fi

  echo
  echo "== IMPORTANT =="
  echo "1) Put the device into DOWNLOAD MODE now."
  echo "   For Samsung: Power + Home + Volume Down, then Volume Up to confirm."
  echo "2) Connect it to this computer via USB."
  echo
  prompt "When the device is in Download Mode and plugged in, press Enter to continue..."

  check_heimdall_device

  local HEIMDALL_CMD=(sudo heimdall flash)

  if [[ "$FW_TYPE" == "dynamic" ]]; then
    echo
    echo "Dynamic partition firmware detected. Building Heimdall command for super.img layout."
    echo "Minimal set: BOOT + SUPER. Optional: VBMETA, MODEM, VENDOR, PRODUCT, ODM, USERDATA."

    if [[ -n "$BOOT" ]]; then
      HEIMDALL_CMD+=(--BOOT "$BOOT")
    fi
    if [[ -n "$SUPER" ]]; then
      HEIMDALL_CMD+=(--SUPER "$SUPER")
    fi
    if [[ -n "$VBMETA" ]] && confirm "Include VBMETA ($VBMETA)?"; then
      HEIMDALL_CMD+=(--VBMETA "$VBMETA")
    fi
    if [[ -n "$MODEM" ]] && confirm "Include MODEM ($MODEM)?"; then
      HEIMDALL_CMD+=(--MODEM "$MODEM")
    fi
    if [[ -n "$VENDOR" ]] && confirm "Include VENDOR ($VENDOR)?"; then
      HEIMDALL_CMD+=(--VENDOR "$VENDOR")
    fi
    if [[ -n "$PRODUCT" ]] && confirm "Include PRODUCT ($PRODUCT)?"; then
      HEIMDALL_CMD+=(--PRODUCT "$PRODUCT")
    fi
    if [[ -n "$ODM" ]] && confirm "Include ODM ($ODM)?"; then
      HEIMDALL_CMD+=(--ODM "$ODM")
    fi
    if [[ -n "$USERDATA" ]] && confirm "Include USERDATA ($USERDATA)? (this may wipe data)"; then
      HEIMDALL_CMD+=(--USERDATA "$USERDATA")
    fi
  else
    echo
    echo "Legacy firmware detected."
    echo "Minimal set: BOOT, RECOVERY, SYSTEM. Optional: MODEM, CACHE, HIDDEN, USERDATA."

    if [[ -n "$BOOT" ]]; then
      HEIMDALL_CMD+=(--BOOT "$BOOT")
    fi
    if [[ -n "$RECOVERY" ]]; then
      HEIMDALL_CMD+=(--RECOVERY "$RECOVERY")
    fi
    if [[ -n "$SYSTEM" ]]; then
      HEIMDALL_CMD+=(--SYSTEM "$SYSTEM")
    fi
    if [[ -n "$MODEM" ]] && confirm "Include MODEM ($MODEM) as well?"; then
      HEIMDALL_CMD+=(--MODEM "$MODEM")
    fi
    if [[ -n "$CACHE" ]] && confirm "Include CACHE ($CACHE) as well?"; then
      HEIMDALL_CMD+=(--CACHE "$CACHE")
    fi
    if [[ -n "$HIDDEN" ]] && confirm "Include HIDDEN ($HIDDEN) as well?"; then
      HEIMDALL_CMD+=(--HIDDEN "$HIDDEN")
    fi
    if [[ -n "$USERDATA" ]] && confirm "Include USERDATA ($USERDATA) as well? (this may wipe data)"; then
      HEIMDALL_CMD+=(--USERDATA "$USERDATA")
    fi
  fi

  echo
  echo "About to run this Heimdall command:"
  echo "  ${HEIMDALL_CMD[*]}"
  echo
  if ! confirm "Proceed with flashing?"; then
    echo "Aborted by user."
    exit 0
  fi

  run_cmd "${HEIMDALL_CMD[@]}"

  echo
  echo "== Flash complete (if no errors were shown) =="
  echo "If the device doesn't reboot automatically, hold the Power key combo to restart."
  echo "Then boot into STOCK RECOVERY and perform:"
  echo "  - Wipe data/factory reset"
  echo "  - Wipe cache/dalvik (if available)"
  echo "  - Reboot system now"
}

flash_custom_recovery() {
  echo "== Flash custom recovery (Samsung / Heimdall) =="
  echo

  local RECOVERY_IMG
  RECOVERY_IMG=$(prompt "Enter path to recovery .img (e.g. TWRP): ")

  if [[ ! -f "$RECOVERY_IMG" ]]; then
    echo "ERROR: Recovery image not found at: $RECOVERY_IMG"
    exit 1
  fi

  echo
  verify_sha256 "$RECOVERY_IMG"

  echo
  echo "Make sure the device is in DOWNLOAD MODE and connected via USB."
  echo "For Samsung: Power + Home + Volume Down, then Volume Up to confirm."
  echo
  prompt "Press Enter once the device is in Download Mode..."

  check_heimdall_device

  echo
  echo "Heimdall command to be executed:"
  echo "  sudo heimdall flash --RECOVERY \"$RECOVERY_IMG\" --no-reboot"
  echo
  if ! confirm "Proceed with flashing recovery?"; then
    echo "Aborted by user."
    exit 0
  fi

  run_cmd sudo heimdall flash --RECOVERY "$RECOVERY_IMG" --no-reboot

  echo
  echo "Recovery flashed. Now:"
  echo "  1) Hold the appropriate key combo to exit Download Mode;"
  echo "  2) Immediately boot into the new recovery (e.g. Power + Home + VolUp on Samsung)."
}

########################################
# ADB sideload helpers (ROM / GApps)
########################################

ensure_adb_device_sideload() {
  echo
  echo "== Checking adb devices (sideload mode) =="
  local attempt=1
  local max_attempts=3
  while (( attempt <= max_attempts )); do
    adb devices
    if adb devices 2>/dev/null | grep -q 'sideload\|recovery\|device$'; then
      echo "Device detected."
      return 0
    fi
    echo "WARNING: No device in sideload/recovery mode (attempt $attempt/$max_attempts)."
    echo "  - On the device, in recovery, go to: Advanced -> ADB Sideload -> Swipe to start."
    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      prompt "Fix the connection and press Enter to retry..."
    fi
  done
  echo "ERROR: No ADB device detected after $max_attempts attempts."
  exit 1
}

adb_sideload_zip() {
  local label="$1"
  echo "== ADB sideload: $label =="
  echo

  local ZIP_PATH
  ZIP_PATH=$(prompt "Enter path to the $label zip: ")
  if [[ ! -f "$ZIP_PATH" ]]; then
    echo "ERROR: Zip not found at: $ZIP_PATH"
    exit 1
  fi

  echo
  verify_sha256 "$ZIP_PATH"

  echo
  echo "On the device, in recovery:"
  echo "  - Go to: Advanced -> ADB Sideload"
  echo "  - Swipe to start sideload"
  echo
  prompt "When the device is in ADB sideload mode, press Enter to continue..."

  ensure_adb_device_sideload

  echo
  echo "About to run: adb sideload \"$ZIP_PATH\""
  echo
  if ! confirm "Proceed with adb sideload?"; then
    echo "Aborted by user."
    exit 0
  fi

  run_cmd adb sideload "$ZIP_PATH"

  echo
  echo "$label sideload complete (if no errors were shown)."
  echo "You can now reboot system from recovery."
}

########################################
# Auto-detect device
########################################

detect_device() {
  echo "== Auto-detect connected device =="
  echo

  local model="" codename=""

  # Try ADB first (device must be booted with USB debugging on, or in recovery)
  if command -v adb >/dev/null 2>&1; then
    if adb devices 2>/dev/null | grep -q 'device$\|recovery$'; then
      model=$(adb shell getprop ro.product.model 2>/dev/null | tr -d '\r' || true)
      codename=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r' || true)
      if [[ -z "$codename" ]]; then
        codename=$(adb shell getprop ro.product.board 2>/dev/null | tr -d '\r' || true)
      fi
    fi
  fi

  if [[ -z "$model" ]]; then
    echo "No device detected via ADB."
    echo "Make sure the device is connected with USB debugging enabled, or in recovery mode."
    echo
    return 1
  fi

  echo "Detected device:"
  echo "  Model:    $model"
  echo "  Codename: $codename"
  echo

  # Try to match against devices.cfg
  if [[ -f "$CONFIG_FILE" ]]; then
    local match_id="" match_label=""
    while IFS='|' read -r id label cfg_model cfg_codename _rest; do
      [[ -z "$id" || "$id" =~ ^# ]] && continue
      # Match by model number (case-insensitive) or codename
      if [[ "${cfg_model,,}" == "${model,,}" ]] || [[ "${cfg_codename,,}" == "${codename,,}" ]]; then
        match_id="$id"
        match_label="$label"
        break
      fi
    done < "$CONFIG_FILE"

    if [[ -n "$match_id" ]]; then
      echo "Matched preset: $match_label [id: $match_id]"
      if confirm "Use this preset to download files?"; then
        download_from_device_config "$match_id"  # skip interactive selection
        return 0
      fi
    else
      echo "No matching preset found in devices.cfg for $model / $codename."
      echo "You can add one manually — see README for the format."
    fi
  fi
}

########################################
# Main menu
########################################

main_menu() {
  require_cmd heimdall
  require_cmd adb

  echo "========================================"
  echo "  Flash Wizard (Samsung / Heimdall & adb)"
  echo "========================================"
  echo "This script can help you:"
  echo "  1) Restore stock firmware from a Samsung ZIP"
  echo "  2) Flash a custom recovery .img (TWRP, etc.)"
  echo "  3) Sideload a custom ROM zip via adb"
  echo "  4) Sideload GApps or other zips via adb"
  echo "  5) Use device presets from devices.cfg to download ROMs/recovery/firmware"
  echo "  6) Auto-detect connected device and match preset"
  echo

  local choice
  choice=$(prompt "Choose an action (1-6, or anything else to quit): ")
  case "$choice" in
    1) flash_stock_firmware ;;
    2) flash_custom_recovery ;;
    3) adb_sideload_zip "custom ROM" ;;
    4) adb_sideload_zip "GApps/other package" ;;
    5) download_from_device_config ;;
    6) detect_device ;;
    *) echo "Exiting."; exit 0 ;;
  esac
}

download_from_device_config() {
  local auto_id=${1:-}  # optional: device id passed by detect_device()

  echo "== Device presets (devices.cfg) =="
  echo

  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "No devices.cfg found at: $CONFIG_FILE"
    echo "Create one (see README) with one device per line:"
    echo "id|label|model|codename|rom_url|twrp_url|eos_url|stock_fw_url|gapps_url"
    return
  fi

  local -a DEV_ROWS=()
  local idx=0

  while IFS='|' read -r id label model codename rom_url twrp_url eos_url stock_url gapps_url; do
    [[ -z "$id" || "$id" =~ ^# ]] && continue
    idx=$((idx + 1))
    DEV_ROWS[idx]="$id|$label|$model|$codename|$rom_url|$twrp_url|$eos_url|$stock_url|$gapps_url"
  done < "$CONFIG_FILE"

  if (( idx == 0 )); then
    echo "devices.cfg exists but no devices were found (lines starting with # are comments)."
    return
  fi

  # If called with an auto-detected device id, skip interactive selection
  if [[ -n "$auto_id" ]]; then
    local found=false
    for ((i = 1; i <= idx; i++)); do
      IFS='|' read -r id label model codename rom_url twrp_url eos_url stock_url gapps_url <<<"${DEV_ROWS[i]}"
      if [[ "$id" == "$auto_id" ]]; then
        found=true
        break
      fi
    done
    if ! $found; then
      echo "ERROR: Device id '$auto_id' not found in devices.cfg."
      return 1
    fi
  else
    echo "Available devices from devices.cfg:"
    local i
    for ((i = 1; i <= idx; i++)); do
      IFS='|' read -r id label model codename _ <<<"${DEV_ROWS[i]}"
      echo "  $i) $label ($model / $codename) [id: $id]"
    done

    echo
    local sel
    sel=$(prompt "Select a device by number (1-$idx): ")
    if ! [[ "$sel" =~ ^[0-9]+$ ]] || (( sel < 1 || sel > idx )); then
      echo "Invalid selection."
      return
    fi

    IFS='|' read -r id label model codename rom_url twrp_url eos_url stock_url gapps_url <<<"${DEV_ROWS[sel]}"
  fi

  echo
  echo "Selected: $label ($model / $codename) [id: $id]"

  local target
  target=$(prompt "Enter target download directory (default: \$HOME/FlashWizard-downloads/$id): ")
  if [[ -z "$target" ]]; then
    target="$HOME/FlashWizard-downloads/$id"
  fi
  mkdir -p "$target"

  download_if_url() {
    local kind=$1
    local url=$2
    [[ -z "$url" ]] && return

    echo
    echo "[$kind]"
    echo "URL: $url"
    if ! confirm "Download this $kind to $target?"; then
      return
    fi

    local base url_noq
    url_noq=${url%%\?*}
    base=$(basename "$url_noq")
    if [[ -z "$base" || "$base" == "/" ]]; then
      base="${id}-${kind}.bin"
    fi

    echo "Downloading -> $target/$base"
    run_cmd wget_retry -O "$target/$base" "$url"

    echo
    verify_sha256 "$target/$base"
  }

  download_if_url "stock firmware" "$stock_url"
  download_if_url "TWRP / recovery" "$twrp_url"
  download_if_url "LineageOS / ROM" "$rom_url"
  download_if_url "/e/OS ROM" "$eos_url"
  download_if_url "GApps" "$gapps_url"

  echo
  echo "Downloads finished (if none failed). Files are in: $target"
}

main_menu

