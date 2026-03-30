/**
 * Maps backend __error_type markers and common terminal output patterns
 * to user-friendly, actionable error messages.
 */

const ERROR_GUIDES = {
  stale_session: {
    title: 'Device session has gone stale',
    message: 'The connection to your device timed out. This usually happens when the device has been in Download Mode too long.',
    steps: [
      'Unplug the USB cable',
      'Hold Power for 10+ seconds until the screen goes black',
      'Press Power to boot normally, then plug USB back in',
      'Try the operation again',
    ],
  },
  signature_verification_failed: {
    title: 'Recovery rejected the ROM',
    message: 'Your stock recovery only accepts manufacturer-signed updates. You need a custom recovery to install third-party software.',
    steps: [
      'Your device is safe — nothing was changed',
      'Go back and install the required custom recovery (TWRP, Replicant Recovery, etc.)',
      'Then retry the sideload',
    ],
  },
  incomplete_transfer: {
    title: 'Transfer may be incomplete',
    message: 'The sideload ended before the full file was sent. This is often caused by a flaky USB connection.',
    steps: [
      'Check your device screen — if it says "Install complete", you\'re done',
      'Use a shorter, higher-quality USB cable',
      'Connect directly to your computer (avoid USB hubs)',
      'Try the push method instead of sideload for more reliable transfers',
    ],
  },
  manual_twrp_install: {
    title: 'Automatic recovery install failed',
    message: 'OSmosis could not install the recovery automatically. You can install it manually.',
    steps: [
      'For TWRP: find your device on twrp.me',
      'For Replicant Recovery: download from replicant.us/supported-devices.php',
      'Download the .img file for your model',
      'Put your device in Download Mode',
      'Use the Flash Recovery page in OSmosis to flash it',
    ],
  },
  manual_recovery_install: {
    title: 'Automatic recovery install failed',
    message: 'OSmosis could not trigger the install automatically via Replicant Recovery.',
    steps: [
      'Reboot into Replicant Recovery manually',
      'Select "Apply update from sdcard" and choose the ROM file',
      'Or select "Apply update from ADB" and use the sideload option in OSmosis',
    ],
  },
  zip_corrupt_wrong_recovery: {
    title: 'ROM file rejected by recovery',
    message: 'Recovery reported the ZIP as corrupt. This usually means the recovery is incompatible with this ROM — not that the file is damaged.',
    steps: [
      'If using stock recovery: install TWRP first, then retry',
      'If using TWRP: make sure you have the latest TWRP for your device',
      'If using Replicant recovery: only Replicant ROM ZIPs are compatible',
      'Re-download the ROM if the issue persists',
    ],
  },
  install_error: {
    title: 'Installation error',
    message: 'Recovery reported an error during installation. Check the terminal output for details.',
    steps: [
      'Your device should still be bootable — reboot to check',
      'If the ROM requires a specific recovery, make sure you have the right one',
      'Try re-downloading the ROM file',
      'Check community forums for known issues with this ROM + device combination',
    ],
  },
  low_battery: {
    title: 'Battery too low',
    message: 'Your device battery is critically low. Flashing with low battery risks bricking the device if it powers off mid-flash.',
    steps: [
      'Charge the device to at least 50% before continuing',
      'If the device won\'t charge, try a different cable or charger',
      'You can also try flashing while the device is plugged into a charger',
    ],
  },
  heimdall_not_found: {
    title: 'Heimdall not installed',
    message: 'Heimdall is needed to flash Samsung devices in Download Mode, but it\'s not installed on this computer.',
    steps: [
      'On Debian/Ubuntu: sudo apt install heimdall-flash',
      'On Fedora: sudo dnf install heimdall',
      'On Arch: sudo pacman -S heimdall',
      'Then retry the operation',
    ],
  },
  adb_unauthorized: {
    title: 'ADB not authorized',
    message: 'Your device is connected but hasn\'t authorized this computer for USB debugging.',
    steps: [
      'Check your device screen for an "Allow USB debugging?" prompt and tap Allow',
      'If you don\'t see the prompt: disconnect and reconnect USB, or toggle USB debugging off and on in Settings > Developer Options',
      'Make sure the device screen is unlocked',
    ],
  },
  bootloader_locked: {
    title: 'Bootloader is locked',
    message: 'Your device\'s bootloader is locked, which prevents installing custom software. You\'ll need to unlock it first.',
    steps: [
      'Go to Settings > About Phone > tap Build Number 7 times to enable Developer Options',
      'Go to Settings > Developer Options > enable OEM Unlocking',
      'Boot into Fastboot/Download Mode',
      'Run: fastboot oem unlock (or fastboot flashing unlock on newer devices)',
      'Warning: unlocking the bootloader erases all data on the device',
    ],
  },
  usb_connection_lost: {
    title: 'USB connection lost during operation',
    message: 'The USB connection was interrupted. This can happen with low-quality cables, loose connections, or USB power saving.',
    steps: [
      'Use a short, high-quality USB cable (not charge-only)',
      'Connect directly to your computer — avoid USB hubs and extension cables',
      'Disable USB power saving: Settings > Power > USB selective suspend (Windows) or TLP (Linux)',
      'Try a different USB port on your computer',
      'Avoid touching or moving the cable during the operation',
    ],
  },
  wrong_partition_size: {
    title: 'Partition size mismatch',
    message: 'The image file is too large for the target partition on your device. This usually means the image is for a different device variant.',
    steps: [
      'Double-check that you downloaded the correct image for your exact device model',
      'Some devices have multiple variants (e.g., international vs carrier) — verify the codename matches',
      'Try re-downloading the image in case of corruption',
    ],
  },
  recovery_not_sideload: {
    title: 'Device is in recovery but not sideload mode',
    message: 'Your device booted into recovery, but ADB sideload hasn\'t been started yet.',
    steps: [
      'On your device screen, navigate to Advanced > ADB Sideload (TWRP) or Apply update from ADB (Replicant Recovery / stock recovery)',
      'Swipe or tap to confirm and start sideload mode',
      'Then retry the operation from this page',
    ],
  },
  no_fastboot_device: {
    title: 'Device is not in fastboot mode',
    message: 'This operation requires your device to be in fastboot mode, but it\'s currently in a different mode (sideload, recovery, etc.).',
    steps: [
      'Use the "Reboot to fastboot" button, or on the device: hold Power + Volume Down until you see "FASTBOOT" on screen',
      'Wait for the page to detect the device in fastboot mode (the status dot will turn purple)',
      'Then retry the operation',
    ],
  },
}

const TERMINAL_PATTERNS = [
  { pattern: /no device in fastboot mode/i, hint: 'Your device is not in fastboot mode. Use the "Reboot to fastboot" action, or on the device hold Power + Volume Down until you see "FASTBOOT" on screen. Then retry.' },
  { pattern: /permission denied/i, hint: 'Permission denied. Try running OSmosis with elevated privileges (sudo), or add your user to the "plugdev" group for USB access: sudo usermod -aG plugdev $USER' },
  { pattern: /device not found|no device/i, hint: 'No device detected. Check that the USB cable is plugged in firmly and supports data transfer (charge-only cables won\'t work). Try a different USB port on the computer, not a USB hub.' },
  { pattern: /connection refused|network.*(unreachable|error)|could not resolve/i, hint: 'Network error. Check your internet connection. If the download server is down, try again later or use an alternative mirror.' },
  { pattern: /disk full|no space left/i, hint: 'Disk full. Free up space on this computer (ROM files can be 500MB–2GB) and try again. Check ~/Osmosis-downloads for old downloads you can delete.' },
  { pattern: /timeout|timed out/i, hint: 'Operation timed out. The device may have disconnected or entered a different mode. Unplug USB, restart the device, and reconnect.' },
  { pattern: /heimdall.*not found|command not found.*heimdall/i, hint: 'Heimdall is not installed. Install it: Ubuntu/Debian: sudo apt install heimdall-flash | Fedora: sudo dnf install heimdall | Arch: sudo pacman -S heimdall' },
  { pattern: /adb.*not found|command not found.*adb/i, hint: 'ADB is not installed. Install it: Ubuntu/Debian: sudo apt install adb | Fedora: sudo dnf install android-tools | Arch: sudo pacman -S android-tools' },
  { pattern: /unauthorized/i, hint: 'USB debugging not authorized. On your device: look for a "Allow USB debugging?" popup and tap Allow. If nothing appears, go to Settings > Developer Options, toggle USB Debugging off and on, then reconnect.' },
  { pattern: /read-only file system/i, hint: 'File system is read-only. The device may not be in the correct mode. Reboot into recovery or Download Mode and try again.' },
  { pattern: /zip.*corrupt|bad.*crc|invalid.*zip/i, hint: 'The ZIP file appears corrupt. Delete it and re-download. If the issue persists, the source file may be damaged — try a different download mirror or ROM version.' },
  { pattern: /low battery|battery.*critical/i, hint: 'Battery critically low. Charge to at least 50% before flashing. A device that powers off mid-flash can become unbootable.' },
  { pattern: /protocol.*init.*fail|libusb.*error/i, hint: 'USB protocol error (stale session). Unplug the USB cable, hold Power for 10+ seconds to restart the device, then reconnect and try again.' },
  { pattern: /cannot.*stat|no such file|file not found/i, hint: 'File not found. The ROM or image file may have been moved or deleted. Check the file path and re-download if needed.' },
  { pattern: /failed.*open.*transport|cannot connect/i, hint: 'Cannot connect to device. Try: 1) Unplug and replug USB cable, 2) Run "adb kill-server" in a terminal, 3) Reconnect and retry.' },
  { pattern: /FAILED\s*\(remote:?\s*\S+\)/i, hint: 'The device rejected the operation. Read the error in parentheses for specifics — common causes include locked bootloader, wrong partition, or incompatible image.' },
  { pattern: /bootloader.*locked|oem.*lock/i, hint: 'Your bootloader is locked. You must unlock it before flashing: go to Settings > Developer Options > OEM Unlocking, then use fastboot oem unlock. This will erase all data.' },
  { pattern: /waiting for.*device|< waiting for/i, hint: 'The tool is waiting for a device connection. Make sure your device is plugged in, powered on, and in the correct mode (Download Mode for Samsung, Fastboot for other brands).' },
  { pattern: /partition.*too small|image.*too large|not enough space/i, hint: 'The image is larger than the target partition. This usually means the image is for a different device variant. Double-check your device model and codename.' },
  { pattern: /error:.*closed|error:.*reset by peer/i, hint: 'The device closed the connection unexpectedly. This can happen when the device reboots or exits sideload mode. Re-enter the correct mode on your device and try again.' },
]

/**
 * Parse terminal output lines for known error types.
 * Returns the first matching error guide, or null.
 */
export function parseErrorType(lines) {
  const text = lines.map(l => l.msg || l || '').join(' ')
  for (const [type, guide] of Object.entries(ERROR_GUIDES)) {
    if (text.includes(`__error_type:${type}`)) {
      return { type, ...guide }
    }
  }
  return null
}

/**
 * Scan terminal output for common error patterns and return hints.
 * Returns an array of hint strings (may be empty).
 */
export function parseTerminalHints(lines) {
  const text = lines.map(l => l.msg || l || '').join('\n')
  const hints = []
  for (const { pattern, hint } of TERMINAL_PATTERNS) {
    if (pattern.test(text)) {
      hints.push(hint)
    }
  }
  return hints
}

/**
 * Get actionable error guide by type name.
 */
export function getErrorGuide(type) {
  return ERROR_GUIDES[type] || null
}
