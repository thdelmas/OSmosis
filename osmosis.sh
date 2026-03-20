#!/usr/bin/env bash
#
# osmosis.sh
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
${C_BOLD}Osmosis${C_RESET} — Interactive Samsung flashing & ROM install helper

${C_BOLD}Usage:${C_RESET}
  ./osmosis.sh [OPTIONS]

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
  8  Backup device partitions (boot, recovery, EFS)
  9  Patch boot.img with Magisk (root)
  10 Check for ROM updates (SourceForge)
  11 Create bootable USB/SD card from ISO/IMG
  12 Start PXE boot server (network install)

${C_BOLD}Files:${C_RESET}
  devices.cfg                Device presets (id|label|model|codename|urls...)
  ~/.osmosis/logs/       Session logs
  ~/.osmosis/backups/    Partition backups

${C_BOLD}Requirements:${C_RESET}
  heimdall-flash, adb, unzip, wget
  Optional: lz4 (for Android 12+ firmware), curl (for update checks)
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

LOG_DIR="$HOME/.osmosis/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/session-$(date +%Y%m%d-%H%M%S).log"

# Duplicate all stdout and stderr to the log file while keeping terminal output.
exec > >(tee -a "$LOG_FILE") 2>&1

info "Osmosis session started: $(date)"
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
# Backup partitions (option 8)
########################################

backup_partitions() {
  header "Backup device partitions"

  local BACKUP_DIR="$HOME/.osmosis/backups/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BACKUP_DIR"
  info "Backup directory: $BACKUP_DIR"
  echo

  # Check if device is accessible via adb
  if ! adb devices 2>/dev/null | grep -q 'device$\|recovery$'; then
    warn "No device detected via ADB."
    info "The device must be connected with USB debugging enabled, or booted into recovery."
    echo
    info "Alternative: if the device is in Download Mode, you can use Heimdall to read partitions."
    if confirm "Try Heimdall partition table dump instead?"; then
      info "Dumping partition table (PIT) via Heimdall..."
      run_cmd sudo heimdall download-pit --output "$BACKUP_DIR/partition-table.pit"
      if [[ -f "$BACKUP_DIR/partition-table.pit" ]]; then
        success "PIT saved to $BACKUP_DIR/partition-table.pit"
      fi
    fi
    return
  fi

  success "Device detected via ADB."
  echo
  echo "Which partitions do you want to back up?"
  echo "Common partitions: boot, recovery, system, userdata, efs"
  echo

  # Check if we have root via adb
  local has_root=false
  if adb shell "su -c 'id'" 2>/dev/null | grep -q 'uid=0'; then
    has_root=true
    success "Root access available — can back up raw partitions via dd."
  else
    warn "No root access — backup limited to accessible files."
    info "For full partition backup, boot into TWRP recovery (which has root)."
  fi
  echo

  # List available block devices if rooted
  if $has_root; then
    local PARTITIONS=("boot" "recovery")
    if confirm "Back up boot and recovery partitions? (recommended minimum)"; then
      for part in "${PARTITIONS[@]}"; do
        local block_dev=""
        # Try common Samsung partition paths
        for path in "/dev/block/platform/*/by-name/$part" "/dev/block/by-name/$part"; do
          local resolved
          resolved=$(adb shell "su -c 'ls $path'" 2>/dev/null | tr -d '\r' || true)
          if [[ -n "$resolved" && "$resolved" != *"No such"* ]]; then
            block_dev="$resolved"
            break
          fi
        done

        if [[ -n "$block_dev" ]]; then
          info "Backing up $part ($block_dev)..."
          run_cmd adb shell "su -c 'dd if=$block_dev'" > "$BACKUP_DIR/${part}.img" 2>/dev/null
          if [[ -f "$BACKUP_DIR/${part}.img" && -s "$BACKUP_DIR/${part}.img" ]]; then
            success "$part -> $BACKUP_DIR/${part}.img ($(du -h "$BACKUP_DIR/${part}.img" | cut -f1))"
          else
            warn "Failed to back up $part."
            rm -f "$BACKUP_DIR/${part}.img"
          fi
        else
          warn "Could not find block device for '$part'."
        fi
      done
    fi

    echo
    if confirm "Back up EFS partition? (contains IMEI — highly recommended)"; then
      local efs_dev=""
      for path in "/dev/block/platform/*/by-name/efs" "/dev/block/by-name/efs"; do
        local resolved
        resolved=$(adb shell "su -c 'ls $path'" 2>/dev/null | tr -d '\r' || true)
        if [[ -n "$resolved" && "$resolved" != *"No such"* ]]; then
          efs_dev="$resolved"
          break
        fi
      done
      if [[ -n "$efs_dev" ]]; then
        info "Backing up EFS ($efs_dev)..."
        run_cmd adb shell "su -c 'dd if=$efs_dev'" > "$BACKUP_DIR/efs.img" 2>/dev/null
        if [[ -f "$BACKUP_DIR/efs.img" && -s "$BACKUP_DIR/efs.img" ]]; then
          success "EFS -> $BACKUP_DIR/efs.img ($(du -h "$BACKUP_DIR/efs.img" | cut -f1))"
        else
          warn "Failed to back up EFS."
        fi
      else
        warn "Could not find EFS block device."
        info "Trying fallback: adb pull /efs ..."
        run_cmd adb pull /efs "$BACKUP_DIR/efs-folder/" 2>/dev/null || warn "EFS folder pull failed."
      fi
    fi
  else
    # No root — limited backup
    info "Without root, backing up accessible data via adb pull."
    if confirm "Pull /sdcard/ contents?"; then
      info "This may take a while for large storage..."
      run_cmd adb pull /sdcard/ "$BACKUP_DIR/sdcard/" 2>/dev/null || warn "sdcard pull failed or partial."
    fi
  fi

  echo
  info "Generating checksums for backup files..."
  (cd "$BACKUP_DIR" && sha256sum *.img 2>/dev/null > checksums.sha256 || true)
  if [[ -f "$BACKUP_DIR/checksums.sha256" && -s "$BACKUP_DIR/checksums.sha256" ]]; then
    success "Checksums saved to $BACKUP_DIR/checksums.sha256"
  fi

  echo
  success "Backup complete. Files in: $BACKUP_DIR"
  ls -lh "$BACKUP_DIR/"
}

########################################
# Magisk patching (option 9)
########################################

patch_boot_magisk() {
  header "Patch boot.img with Magisk"

  local BOOT_IMG
  BOOT_IMG=$(prompt "Enter path to boot.img to patch: ")
  if [[ ! -f "$BOOT_IMG" ]]; then
    error "boot.img not found at: $BOOT_IMG"
    return 1
  fi

  verify_sha256 "$BOOT_IMG"
  echo

  # Check if device is connected
  if ! adb devices 2>/dev/null | grep -q 'device$'; then
    error "Device not detected via ADB (must be booted normally, not recovery)."
    info "Magisk patching requires:"
    echo "  1) Magisk app installed on the device"
    echo "  2) Device booted normally with USB debugging enabled"
    return 1
  fi

  # Check if Magisk is installed
  local magisk_pkg=""
  for pkg in "com.topjohnwu.magisk" "io.github.vvb2060.magisk" "com.topjohnwu.magisk.debug"; do
    if adb shell "pm list packages" 2>/dev/null | grep -q "$pkg"; then
      magisk_pkg="$pkg"
      break
    fi
  done

  if [[ -z "$magisk_pkg" ]]; then
    error "Magisk app not found on device."
    info "Install Magisk first from: https://github.com/topjohnwu/Magisk/releases"
    return 1
  fi
  success "Magisk app found: $magisk_pkg"
  echo

  # Push boot.img to device
  local device_path="/sdcard/Download/boot-to-patch.img"
  info "Pushing boot.img to device..."
  run_cmd adb push "$BOOT_IMG" "$device_path"
  echo

  info "Now open the Magisk app on the device and:"
  echo -e "  ${C_BOLD}1${C_RESET}) Tap 'Install' next to Magisk"
  echo -e "  ${C_BOLD}2${C_RESET}) Choose 'Select and Patch a File'"
  echo -e "  ${C_BOLD}3${C_RESET}) Navigate to Download/ and select 'boot-to-patch.img'"
  echo -e "  ${C_BOLD}4${C_RESET}) Tap 'LET'S GO' and wait for patching to complete"
  echo
  prompt "Press Enter when Magisk has finished patching..."

  # Pull the patched file back
  local patched_dir
  patched_dir=$(dirname "$BOOT_IMG")
  info "Looking for patched boot image on device..."

  local patched_device
  patched_device=$(adb shell "ls -t /sdcard/Download/magisk_patched-*.img 2>/dev/null | head -1" | tr -d '\r')

  if [[ -z "$patched_device" || "$patched_device" == *"No such"* ]]; then
    warn "Could not find patched file automatically."
    patched_device=$(prompt "Enter the path on device (e.g. /sdcard/Download/magisk_patched-XXXXX.img): ")
  fi

  local patched_local="$patched_dir/magisk_patched-boot.img"
  info "Pulling patched image to $patched_local..."
  run_cmd adb pull "$patched_device" "$patched_local"

  if [[ -f "$patched_local" ]]; then
    echo
    verify_sha256 "$patched_local"
    echo
    success "Patched boot image saved to: $patched_local"
    info "You can now flash it with:"
    echo "  sudo heimdall flash --BOOT \"$patched_local\""
    echo
    if confirm "Flash patched boot.img now via Heimdall?"; then
      info "Put the device into DOWNLOAD MODE now."
      info "For Samsung: Power + Home + Volume Down, then Volume Up to confirm."
      prompt "Press Enter when the device is in Download Mode..."
      check_heimdall_device
      run_cmd sudo heimdall flash --BOOT "$patched_local"
      success "Patched boot.img flashed!"
    fi
  else
    error "Failed to pull patched boot image."
  fi
}

########################################
# ROM update checker (option 10)
########################################

check_rom_updates() {
  header "Check for ROM updates"

  require_cmd curl

  if [[ ! -f "$CONFIG_FILE" ]]; then
    error "No devices.cfg found. Cannot check updates without device presets."
    return 1
  fi

  local -a DEV_ROWS=()
  local idx=0

  while IFS='|' read -r id label model codename rom_url twrp_url eos_url stock_url gapps_url; do
    [[ -z "$id" || "$id" =~ ^# ]] && continue
    idx=$((idx + 1))
    DEV_ROWS[idx]="$id|$label|$model|$codename|$rom_url|$twrp_url|$eos_url|$stock_url|$gapps_url"
  done < "$CONFIG_FILE"

  if (( idx == 0 )); then
    warn "No devices found in devices.cfg."
    return
  fi

  echo "Checking available builds for all configured devices..."
  echo

  for ((i = 1; i <= idx; i++)); do
    IFS='|' read -r id label model codename rom_url twrp_url eos_url stock_url gapps_url <<<"${DEV_ROWS[i]}"
    echo -e "${C_BOLD}$label${C_RESET} ($model / $codename)"

    # Check SourceForge for LineageOS builds
    if [[ -n "$rom_url" && "$rom_url" == *sourceforge.net* ]]; then
      # Extract the project path to query the RSS/file listing
      local sf_project sf_path
      sf_project=$(echo "$rom_url" | sed -n 's|.*sourceforge.net/projects/\([^/]*\)/.*|\1|p')
      sf_path=$(echo "$rom_url" | sed -n 's|.*files/\(.*\)/download|\1|p')
      sf_path=$(dirname "$sf_path")

      if [[ -n "$sf_project" && -n "$sf_path" ]]; then
        local api_url="https://sourceforge.net/projects/$sf_project/files/$sf_path/"
        info "LineageOS — checking $sf_project/$sf_path ..."

        local latest
        latest=$(curl -sL "$api_url" 2>/dev/null \
          | grep -oP 'title="lineage-[^"]*\.zip"' \
          | head -3 \
          | sed 's/title="//;s/"//' || true)

        if [[ -n "$latest" ]]; then
          echo "  Latest builds found:"
          echo "$latest" | while read -r fname; do
            echo -e "    ${C_GREEN}$fname${C_RESET}"
          done
          # Compare with configured URL
          local configured_file
          configured_file=$(basename "${rom_url%%\?*}")
          echo "  Currently configured: $configured_file"
        else
          warn "  Could not fetch LineageOS build list."
        fi
      fi
    fi

    # Check SourceForge for /e/OS builds
    if [[ -n "$eos_url" && "$eos_url" == *sourceforge.net* ]]; then
      local sf_project_e sf_path_e
      sf_project_e=$(echo "$eos_url" | sed -n 's|.*sourceforge.net/projects/\([^/]*\)/.*|\1|p')
      sf_path_e=$(echo "$eos_url" | sed -n 's|.*files/\(.*\)/download|\1|p')
      sf_path_e=$(dirname "$sf_path_e")

      if [[ -n "$sf_project_e" && -n "$sf_path_e" ]]; then
        local api_url_e="https://sourceforge.net/projects/$sf_project_e/files/$sf_path_e/"
        info "/e/OS — checking $sf_project_e/$sf_path_e ..."

        local latest_e
        latest_e=$(curl -sL "$api_url_e" 2>/dev/null \
          | grep -oP 'title="e-[^"]*\.zip"' \
          | head -3 \
          | sed 's/title="//;s/"//' || true)

        if [[ -n "$latest_e" ]]; then
          echo "  Latest builds found:"
          echo "$latest_e" | while read -r fname; do
            echo -e "    ${C_GREEN}$fname${C_RESET}"
          done
          local configured_file_e
          configured_file_e=$(basename "${eos_url%%\?*}")
          echo "  Currently configured: $configured_file_e"
        else
          warn "  Could not fetch /e/OS build list."
        fi
      fi
    fi

    echo
  done

  info "To update a URL in devices.cfg, edit the file directly or re-run the wizard."
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
# Create bootable USB/SD (option 11)
########################################

is_system_drive() {
  # Check if a device hosts /, /boot, /boot/efi, or swap
  local dev_name="$1"
  local mounts
  mounts=$(lsblk -ln -o NAME,MOUNTPOINT "/dev/$dev_name" 2>/dev/null)
  echo "$mounts" | grep -qE '\s(/|/boot|/boot/efi|\[SWAP\])$'
}

create_bootable_device() {
  header "Create bootable USB/SD card"

  local IMAGE_PATH
  IMAGE_PATH=$(prompt "Enter path to ISO or IMG file: ")
  if [[ ! -f "$IMAGE_PATH" ]]; then
    error "Image file not found at: $IMAGE_PATH"
    return 1
  fi

  verify_sha256 "$IMAGE_PATH"
  echo

  local IMAGE_SIZE
  IMAGE_SIZE=$(stat -c%s "$IMAGE_PATH" 2>/dev/null || stat -f%z "$IMAGE_PATH" 2>/dev/null)

  # List removable block devices (excluding system drives)
  info "Scanning for removable devices..."
  echo
  echo "Available removable devices:"
  echo "-----------------------------------------------------------"

  local -a DEV_LIST=()
  local idx=0

  while IFS= read -r line; do
    local name size model tran rm_flag
    name=$(echo "$line" | awk '{print $1}')
    size=$(echo "$line" | awk '{print $2}')
    tran=$(echo "$line" | awk '{print $3}')
    model=$(echo "$line" | awk '{$1=$2=$3=""; print}' | sed 's/^ *//')
    rm_flag=$(lsblk -no RM "/dev/$name" 2>/dev/null | head -1 | tr -d ' ')

    # Filter: must be removable or USB, must NOT be a system drive
    if [[ "$rm_flag" == "1" || "$tran" == "usb" ]]; then
      if is_system_drive "$name"; then
        continue
      fi

      local dev_bytes large_flag=""
      dev_bytes=$(lsblk -bno SIZE "/dev/$name" 2>/dev/null | head -1 | tr -d ' ')
      if [[ -n "$dev_bytes" ]] && (( dev_bytes > 137438953472 )); then
        large_flag=" ${C_YELLOW}[LARGE >128GB]${C_RESET}"
      fi

      idx=$((idx + 1))
      DEV_LIST[idx]="/dev/$name"
      echo -e "  $idx) /dev/$name — $size — ${model:-Unknown device} ($tran)${large_flag}"
    fi
  done < <(lsblk -dno NAME,SIZE,TRAN,MODEL 2>/dev/null | grep -v '^loop')

  if (( idx == 0 )); then
    warn "No removable devices found."
    info "Insert a USB drive or SD card and try again."
    return 1
  fi
  echo

  local sel
  sel=$(prompt "Select target device (1-$idx): ")
  if ! [[ "$sel" =~ ^[0-9]+$ ]] || (( sel < 1 || sel > idx )); then
    echo "Invalid selection."
    return 1
  fi

  local TARGET="${DEV_LIST[$sel]}"
  local TARGET_NAME="${TARGET#/dev/}"

  # Safety: reject system drives (belt + suspenders)
  if is_system_drive "$TARGET_NAME"; then
    error "$TARGET is your system drive — refusing to write!"
    return 1
  fi

  # Safety: check image fits on target
  local TARGET_SIZE
  TARGET_SIZE=$(lsblk -bno SIZE "$TARGET" 2>/dev/null | head -1 | tr -d ' ')
  if [[ -n "$TARGET_SIZE" && -n "$IMAGE_SIZE" ]] && (( IMAGE_SIZE > TARGET_SIZE )); then
    error "Image ($(( IMAGE_SIZE / 1048576 )) MB) is larger than drive ($(( TARGET_SIZE / 1048576 )) MB)."
    return 1
  fi

  # Safety: warn about large drives
  if [[ -n "$TARGET_SIZE" ]] && (( TARGET_SIZE > 137438953472 )); then
    echo
    warn "The selected drive is larger than 128 GB."
    warn "Double-check this is the correct device!"
    echo
  fi

  warn "TARGET: $TARGET"
  warn "ALL DATA ON $TARGET WILL BE ERASED!"
  echo

  if ! confirm "Are you sure you want to write $(basename "$IMAGE_PATH") to $TARGET?"; then
    echo "Aborted by user."
    return 0
  fi

  # Unmount any mounted partitions
  info "Unmounting partitions on $TARGET..."
  for part in "${TARGET}"*; do
    if mountpoint -q "$part" 2>/dev/null || mount | grep -q "^$part "; then
      run_cmd sudo umount "$part" 2>/dev/null || true
    fi
  done

  echo
  info "Writing image to $TARGET..."
  run_cmd sudo dd if="$IMAGE_PATH" of="$TARGET" bs=4M status=progress conv=fsync
  local DD_RC=$?

  echo
  info "Syncing..."
  run_cmd sync

  if (( DD_RC != 0 )); then
    error "Failed to write image to device."
    return 1
  fi

  # Post-write verification
  echo
  info "Verifying written data..."
  local SOURCE_HASH DEVICE_HASH
  SOURCE_HASH=$(sha256sum "$IMAGE_PATH" | awk '{print $1}')
  info "Source SHA256: $SOURCE_HASH"

  local BLOCK_COUNT=$(( (IMAGE_SIZE + 4194303) / 4194304 ))
  DEVICE_HASH=$(sudo dd if="$TARGET" bs=4M count="$BLOCK_COUNT" status=none 2>/dev/null | head -c "$IMAGE_SIZE" | sha256sum | awk '{print $1}')
  info "Device SHA256: $DEVICE_HASH"

  if [[ "$SOURCE_HASH" == "$DEVICE_HASH" ]]; then
    success "Verification PASSED — written data matches source image."
  else
    error "Verification FAILED — the data on the device does not match the source!"
    error "Source: $SOURCE_HASH"
    error "Device: $DEVICE_HASH"
    return 1
  fi

  echo
  success "Bootable device created on $TARGET!"
  info "You can now safely remove the device."
}

########################################
# PXE boot server (option 12)
########################################

start_pxe_server() {
  header "PXE Boot Server"

  require_cmd dnsmasq

  local PXE_DIR="$HOME/.osmosis/pxe"
  local TFTP_ROOT="$PXE_DIR/tftpboot"
  mkdir -p "$TFTP_ROOT"

  # Select network interface
  echo "Available network interfaces:"
  local -a IFACE_LIST=()
  local idx=0
  while IFS= read -r iface; do
    [[ "$iface" == "lo" ]] && continue
    idx=$((idx + 1))
    IFACE_LIST[idx]="$iface"
    local state
    state=$(cat "/sys/class/net/$iface/operstate" 2>/dev/null || echo "unknown")
    echo "  $idx) $iface ($state)"
  done < <(ls /sys/class/net/ 2>/dev/null)

  if (( idx == 0 )); then
    error "No network interfaces found."
    return 1
  fi
  echo

  local sel
  sel=$(prompt "Select interface (1-$idx): ")
  if ! [[ "$sel" =~ ^[0-9]+$ ]] || (( sel < 1 || sel > idx )); then
    echo "Invalid selection."
    return 1
  fi
  local IFACE="${IFACE_LIST[$sel]}"

  # Detect IP
  local SERVER_IP
  SERVER_IP=$(ip -4 addr show "$IFACE" 2>/dev/null | grep -oP 'inet \K[\d.]+' | head -1)
  if [[ -z "$SERVER_IP" ]]; then
    SERVER_IP=$(prompt "Could not detect IP. Enter server IP address: ")
  fi
  info "Server IP: $SERVER_IP"
  info "Interface: $IFACE"
  echo

  # Optional boot image
  local IMAGE_PATH
  IMAGE_PATH=$(prompt "Path to boot image (ISO/IMG, leave empty to skip): ")
  if [[ -n "$IMAGE_PATH" && -f "$IMAGE_PATH" ]]; then
    local img_name
    img_name=$(basename "$IMAGE_PATH")
    if [[ ! -f "$TFTP_ROOT/$img_name" ]]; then
      info "Copying $img_name to TFTP root..."
      cp "$IMAGE_PATH" "$TFTP_ROOT/$img_name"
    fi
    success "Image available in TFTP root: $img_name"
  fi

  # Copy PXE bootloader if available
  local PXELINUX=""
  for p in /usr/lib/PXELINUX/pxelinux.0 /usr/share/syslinux/pxelinux.0 /usr/lib/syslinux/pxelinux.0; do
    if [[ -f "$p" ]]; then
      PXELINUX="$p"
      break
    fi
  done

  if [[ -n "$PXELINUX" ]]; then
    cp "$PXELINUX" "$TFTP_ROOT/pxelinux.0"
    info "PXE bootloader: $PXELINUX"

    # Copy syslinux modules
    for moddir in /usr/lib/syslinux/modules/bios /usr/share/syslinux /usr/lib/syslinux; do
      if [[ -d "$moddir" ]]; then
        for mod in ldlinux.c32 menu.c32 libutil.c32 libcom32.c32; do
          [[ -f "$moddir/$mod" ]] && cp "$moddir/$mod" "$TFTP_ROOT/"
        done
        break
      fi
    done
  else
    warn "pxelinux.0 not found. Install with: sudo apt install pxelinux syslinux-common"
  fi

  # Create PXE menu
  mkdir -p "$TFTP_ROOT/pxelinux.cfg"
  cat > "$TFTP_ROOT/pxelinux.cfg/default" <<PXEMENU
DEFAULT menu.c32
PROMPT 0
MENU TITLE Osmosis PXE Boot
TIMEOUT 300

LABEL local
  MENU LABEL Boot from local disk
  LOCALBOOT 0
PXEMENU

  # DHCP mode
  echo
  echo "DHCP mode:"
  echo "  1) Proxy — use alongside existing DHCP server (recommended)"
  echo "  2) Standalone — Osmosis provides DHCP"
  local mode_sel
  mode_sel=$(prompt "Select mode (1-2, default 1): ")
  local MODE="proxy"
  [[ "$mode_sel" == "2" ]] && MODE="standalone"

  # Build dnsmasq config
  local DNSMASQ_CONF="$PXE_DIR/dnsmasq-pxe.conf"
  cat > "$DNSMASQ_CONF" <<DNSEOF
interface=$IFACE
bind-interfaces
enable-tftp
tftp-root=$TFTP_ROOT
log-dhcp
DNSEOF

  if [[ "$MODE" == "proxy" ]]; then
    cat >> "$DNSMASQ_CONF" <<DNSEOF
dhcp-range=$SERVER_IP,proxy
pxe-service=x86PC,"Osmosis PXE",pxelinux
DNSEOF
    info "Mode: DHCP proxy"
  else
    local RANGE_START RANGE_END
    IFS='.' read -ra IP_PARTS <<< "$SERVER_IP"
    RANGE_START="${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}.100"
    RANGE_END="${IP_PARTS[0]}.${IP_PARTS[1]}.${IP_PARTS[2]}.200"
    cat >> "$DNSMASQ_CONF" <<DNSEOF
dhcp-range=$RANGE_START,$RANGE_END,12h
dhcp-boot=pxelinux.0,osmosis,$SERVER_IP
DNSEOF
    info "Mode: Standalone DHCP ($RANGE_START - $RANGE_END)"
  fi

  echo
  info "TFTP root: $TFTP_ROOT"
  info "Config: $DNSMASQ_CONF"
  echo
  info "Starting PXE server on $IFACE ($SERVER_IP)..."
  info "Press Ctrl+C to stop."
  echo

  run_cmd sudo dnsmasq --no-daemon -C "$DNSMASQ_CONF"

  echo
  info "PXE server stopped."
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
  echo -e "  ${C_BOLD}8${C_RESET}) Backup device partitions (boot, recovery, EFS)"
  echo -e "  ${C_BOLD}9${C_RESET}) Patch boot.img with Magisk (root)"
  echo -e "  ${C_BOLD}10${C_RESET}) Check for ROM updates"
  echo -e "  ${C_BOLD}11${C_RESET}) Create bootable USB/SD card from ISO/IMG"
  echo -e "  ${C_BOLD}12${C_RESET}) Start PXE boot server (network install)"
  echo

  local choice
  choice=$(prompt "Choose an action (1-12, or anything else to quit): ")
  case "$choice" in
    1) flash_stock_firmware ;;
    2) flash_custom_recovery ;;
    3) adb_sideload_zip "custom ROM" ;;
    4) adb_sideload_zip "GApps/other package" ;;
    5) download_from_device_config ;;
    6) detect_device ;;
    7) full_workflow ;;
    8) backup_partitions ;;
    9) patch_boot_magisk ;;
    10) check_rom_updates ;;
    11) create_bootable_device ;;
    12) start_pxe_server ;;
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
  target=$(prompt "Enter target download directory (default: \$HOME/Osmosis-downloads/$id): ")
  if [[ -z "$target" ]]; then
    target="$HOME/Osmosis-downloads/$id"
  fi
  mkdir -p "$target"

  local _dl_failures=0

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
    if run_cmd wget_retry -O "$target/$base" "$url"; then
      echo
      verify_sha256 "$target/$base"
    else
      error "Download failed for $kind."
      rm -f "$target/$base"
      _dl_failures=$((_dl_failures + 1))
    fi
  }

  download_if_url "stock firmware" "$stock_url"
  download_if_url "TWRP / recovery" "$twrp_url"
  download_if_url "LineageOS / ROM" "$rom_url"
  download_if_url "/e/OS ROM" "$eos_url"
  download_if_url "GApps" "$gapps_url"

  echo
  if (( _dl_failures > 0 )); then
    error "$_dl_failures download(s) failed. Check the errors above."
  else
    success "All downloads finished. Files are in: $target"
  fi
}

main_menu

