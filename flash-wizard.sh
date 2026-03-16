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

########################################
# Colors (disabled if not a terminal)
########################################

if [[ -t 1 ]]; then
  C_RESET='\033[0m'
  C_BOLD='\033[1m'
  C_RED='\033[0;31m'
  C_GREEN='\033[0;32m'
  C_YELLOW='\033[0;33m'
  C_BLUE='\033[0;34m'
  C_CYAN='\033[0;36m'
else
  C_RESET='' C_BOLD='' C_RED='' C_GREEN='' C_YELLOW='' C_BLUE='' C_CYAN=''
fi

info()    { echo -e "${C_BLUE}[INFO]${C_RESET} $*"; }
success() { echo -e "${C_GREEN}[OK]${C_RESET} $*"; }
warn()    { echo -e "${C_YELLOW}[WARN]${C_RESET} $*"; }
error()   { echo -e "${C_RED}[ERROR]${C_RESET} $*"; }
header()  { echo -e "\n${C_BOLD}${C_CYAN}== $* ==${C_RESET}\n"; }

########################################
# --help / arg parsing
########################################

usage() {
  cat <<HELPEOF
${C_BOLD}FlashWizard${C_RESET} — Interactive Samsung flashing & ROM install helper

${C_BOLD}Usage:${C_RESET}
  ./flash-wizard.sh [OPTIONS]

${C_BOLD}Options:${C_RESET}
  --dry-run   Show commands without executing them
  --help      Show this help message and exit

${C_BOLD}Menu options (interactive):${C_RESET}
  1  Restore stock firmware from a Samsung ZIP (Heimdall)
  2  Flash a custom recovery .img (TWRP, etc.)
  3  Sideload a custom ROM zip via adb
  4  Sideload GApps or other zips via adb
  5  Use device presets from devices.cfg
  6  Auto-detect connected device and match preset
  7  Full workflow: restore + recovery + ROM + GApps in one session

${C_BOLD}Files:${C_RESET}
  devices.cfg   Device presets (id|label|model|codename|urls...)
  ~/.flashwizard/logs/   Session logs

${C_BOLD}Requirements:${C_RESET}
  heimdall-flash, adb, unzip, wget
  Optional: lz4 (for Android 12+ firmware)
HELPEOF
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --help|-h) usage; exit 0 ;;
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

info "FlashWizard session started: $(date)"
info "Log file: $LOG_FILE"
echo

if $DRY_RUN; then
  warn "DRY-RUN mode enabled — no destructive commands will be executed."
  echo
fi

# Wrapper: prints the command, and skips execution in dry-run mode.
run_cmd() {
  echo -e "  ${C_CYAN}>>${C_RESET} $*"
  if $DRY_RUN; then
    warn "  [DRY-RUN] Skipped."
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
    error "'$cmd' is not installed or not in PATH."
    if [[ "$cmd" == "heimdall" ]]; then
      info "Install with:  sudo apt update && sudo apt install heimdall-flash"
    elif [[ "$cmd" == "adb" ]]; then
      info "Install with:  sudo apt update && sudo apt install adb"
    fi
    exit 1
  fi
}

wget_retry() {
  local max_attempts=3
  local attempt=1
  while (( attempt <= max_attempts )); do
    info "Download attempt $attempt/$max_attempts..."
    if wget --progress=bar:force --tries=1 --timeout=30 "$@" 2>&1; then
      success "Download complete."
      return 0
    fi
    warn "Download failed (attempt $attempt/$max_attempts)."
    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      info "Retrying in 3 seconds..."
      sleep 3
    fi
  done
  error "Download failed after $max_attempts attempts."
  return 1
}

verify_sha256() {
  local file=$1
  local expected=${2:-}  # optional: expected hash (empty = just display)

  if [[ ! -f "$file" ]]; then
    warn "Cannot verify checksum — file not found: $file"
    return 1
  fi

  local actual
  actual=$(sha256sum "$file" | awk '{print $1}')

  if [[ -n "$expected" ]]; then
    if [[ "$actual" == "$expected" ]]; then
      success "SHA256 OK: $actual"
      return 0
    else
      error "SHA256 MISMATCH!"
      echo "  Expected: $expected"
      echo "  Got:      $actual"
      return 1
    fi
  else
    info "SHA256: $actual"
    return 0
  fi
}

########################################
# Heimdall / Samsung helpers
########################################

check_heimdall_device() {
  echo
  header "Checking Heimdall device detection (with sudo)"
  local attempt=1
  local max_attempts=3
  while (( attempt <= max_attempts )); do
    if run_cmd sudo heimdall detect; then
      return 0
    fi
    warn "Device not detected (attempt $attempt/$max_attempts)."
    info "Check that the device is in DOWNLOAD MODE and the USB cable is connected."
    info "For Samsung: Power + Home + Volume Down, then Volume Up to confirm."
    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      prompt "Fix the connection and press Enter to retry..."
    fi
  done
  error "Heimdall could not detect a device after $max_attempts attempts."
  exit 1
}

flash_stock_firmware() {
  header "Stock firmware restore (Samsung / Heimdall)"
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
    error "Firmware zip not found at: $FW_ZIP"
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
  header "Extracting main firmware zip"
  unzip -o "$FW_ZIP" -d "$WORK_DIR"

  cd "$WORK_DIR"

  echo
  header "Extracting BL/AP/CP/CSC tar.md5 files (if present)"
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
      header "Decompressing .lz4 files"
      for lz4f in "${lz4_files[@]}"; do
        echo "Decompressing $lz4f"
        lz4 -d -f "$lz4f" "${lz4f%.lz4}"
      done
    else
      echo
      warn ".lz4 files found but 'lz4' command not available."
      info "Install with:  sudo apt install lz4"
      warn "Continuing without decompression — Heimdall cannot flash .lz4 directly."
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
  success "Flash complete (if no errors were shown)."
  info "If the device doesn't reboot automatically, hold the Power key combo to restart."
  info "Then boot into STOCK RECOVERY and perform:"
  echo "  - Wipe data/factory reset"
  echo "  - Wipe cache/dalvik (if available)"
  echo "  - Reboot system now"
}

flash_custom_recovery() {
  header "Flash custom recovery (Samsung / Heimdall)"
  echo

  local RECOVERY_IMG
  RECOVERY_IMG=$(prompt "Enter path to recovery .img (e.g. TWRP): ")

  if [[ ! -f "$RECOVERY_IMG" ]]; then
    error "Recovery image not found at: $RECOVERY_IMG"
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
  header "Checking adb devices (sideload mode)"
  local attempt=1
  local max_attempts=3
  while (( attempt <= max_attempts )); do
    adb devices
    if adb devices 2>/dev/null | grep -q 'sideload\|recovery\|device$'; then
      success "Device detected."
      return 0
    fi
    warn "No device in sideload/recovery mode (attempt $attempt/$max_attempts)."
    echo "  - On the device, in recovery, go to: Advanced -> ADB Sideload -> Swipe to start."
    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      prompt "Fix the connection and press Enter to retry..."
    fi
  done
  error "No ADB device detected after $max_attempts attempts."
  exit 1
}

adb_sideload_zip() {
  local label="$1"
  header "ADB sideload: $label"
  echo

  local ZIP_PATH
  ZIP_PATH=$(prompt "Enter path to the $label zip: ")
  if [[ ! -f "$ZIP_PATH" ]]; then
    error "Zip not found at: $ZIP_PATH"
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
  success "$label sideload complete (if no errors were shown)."
  info "You can now reboot system from recovery."
}

########################################
# Auto-detect device
########################################

detect_device() {
  header "Auto-detect connected device"

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
    warn "No device detected via ADB."
    info "Make sure the device is connected with USB debugging enabled, or in recovery mode."
    echo
    return 1
  fi

  success "Detected device:"
  echo "  Model:    $model"
  echo "  Codename: $codename"
  echo

  # Try to match against devices.cfg
  if [[ -f "$CONFIG_FILE" ]]; then
    local match_id="" match_label=""
    while IFS='|' read -r id label cfg_model cfg_codename _rest; do
      [[ -z "$id" || "$id" =~ ^# ]] && continue
      if [[ "${cfg_model,,}" == "${model,,}" ]] || [[ "${cfg_codename,,}" == "${codename,,}" ]]; then
        match_id="$id"
        match_label="$label"
        break
      fi
    done < "$CONFIG_FILE"

    if [[ -n "$match_id" ]]; then
      success "Matched preset: $match_label [id: $match_id]"
      if confirm "Use this preset to download files?"; then
        download_from_device_config "$match_id"
        return 0
      fi
    else
      warn "No matching preset found in devices.cfg for $model / $codename."
      info "You can add one manually — see README for the format."
    fi
  fi
}

########################################
# Full workflow (option 7)
########################################

full_workflow() {
  header "Full workflow: stock restore + recovery + ROM + GApps"
  echo "This guided workflow will walk you through the complete process:"
  echo -e "  ${C_BOLD}Step 1${C_RESET} — Restore stock firmware via Heimdall"
  echo -e "  ${C_BOLD}Step 2${C_RESET} — Flash custom recovery (TWRP)"
  echo -e "  ${C_BOLD}Step 3${C_RESET} — Sideload custom ROM via adb"
  echo -e "  ${C_BOLD}Step 4${C_RESET} — Sideload GApps via adb (optional)"
  echo
  echo "You can skip any step by answering 'n' when prompted."
  echo

  # Step 1: Stock firmware
  if confirm "Step 1: Restore stock firmware?"; then
    flash_stock_firmware
    echo
    success "Step 1 complete."
    echo
    info "The device should now be on stock firmware."
    info "If it rebooted, put it back into Download Mode for Step 2."
    prompt "Press Enter when ready for Step 2..."
  else
    info "Skipping Step 1 (stock firmware restore)."
  fi
  echo

  # Step 2: Custom recovery
  if confirm "Step 2: Flash custom recovery (TWRP)?"; then
    flash_custom_recovery
    echo
    success "Step 2 complete."
    echo
    info "Now boot into the new recovery:"
    info "  Power + Home + Volume Up (Samsung)"
    info "Once in TWRP, do a full wipe (Wipe -> Advanced Wipe -> select all except SD card)."
    prompt "Press Enter when you're in recovery and ready for Step 3..."
  else
    info "Skipping Step 2 (custom recovery)."
  fi
  echo

  # Step 3: Sideload ROM
  if confirm "Step 3: Sideload custom ROM?"; then
    adb_sideload_zip "custom ROM"
    echo
    success "Step 3 complete."
    echo
    info "Do NOT reboot yet if you want to install GApps."
    info "In TWRP, go back and start ADB sideload again for Step 4."
    prompt "Press Enter when ready for Step 4..."
  else
    info "Skipping Step 3 (custom ROM sideload)."
  fi
  echo

  # Step 4: GApps
  if confirm "Step 4: Sideload GApps?"; then
    adb_sideload_zip "GApps"
    echo
    success "Step 4 complete."
  else
    info "Skipping Step 4 (GApps)."
  fi
  echo

  success "Full workflow finished!"
  info "You can now reboot from recovery: Reboot -> System."
  info "First boot may take 5-10 minutes — this is normal."
}

########################################
# Main menu
########################################

main_menu() {
  require_cmd heimdall
  require_cmd adb

  echo -e "${C_BOLD}${C_CYAN}========================================${C_RESET}"
  echo -e "${C_BOLD}  Flash Wizard (Samsung / Heimdall & adb)${C_RESET}"
  echo -e "${C_BOLD}${C_CYAN}========================================${C_RESET}"
  echo "Choose an action:"
  echo -e "  ${C_BOLD}1${C_RESET}) Restore stock firmware from a Samsung ZIP"
  echo -e "  ${C_BOLD}2${C_RESET}) Flash a custom recovery .img (TWRP, etc.)"
  echo -e "  ${C_BOLD}3${C_RESET}) Sideload a custom ROM zip via adb"
  echo -e "  ${C_BOLD}4${C_RESET}) Sideload GApps or other zips via adb"
  echo -e "  ${C_BOLD}5${C_RESET}) Use device presets from devices.cfg"
  echo -e "  ${C_BOLD}6${C_RESET}) Auto-detect connected device and match preset"
  echo -e "  ${C_BOLD}7${C_RESET}) Full workflow: restore + recovery + ROM + GApps"
  echo

  local choice
  choice=$(prompt "Choose an action (1-7, or anything else to quit): ")
  case "$choice" in
    1) flash_stock_firmware ;;
    2) flash_custom_recovery ;;
    3) adb_sideload_zip "custom ROM" ;;
    4) adb_sideload_zip "GApps/other package" ;;
    5) download_from_device_config ;;
    6) detect_device ;;
    7) full_workflow ;;
    *) echo "Exiting."; exit 0 ;;
  esac
}

download_from_device_config() {
  local auto_id=${1:-}  # optional: device id passed by detect_device()

  header "Device presets (devices.cfg)"
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

