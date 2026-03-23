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
    message: 'Your stock recovery only accepts manufacturer-signed updates. You need a custom recovery like TWRP to install third-party software.',
    steps: [
      'Your device is safe — nothing was changed',
      'Go back and install a custom recovery (TWRP)',
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
    message: 'OSmosis could not install TWRP automatically. You can install it manually.',
    steps: [
      'Find your device on twrp.me',
      'Download the .img file for your model',
      'Put your device in Download Mode',
      'Use the Flash Recovery page in OSmosis to flash it',
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
}

const TERMINAL_PATTERNS = [
  { pattern: /permission denied/i, hint: 'Try running OSmosis with elevated privileges (sudo), or check that your user has USB device access.' },
  { pattern: /device not found|no device/i, hint: 'Make sure the USB cable is plugged in and supports data transfer (not charge-only). Try a different USB port.' },
  { pattern: /connection refused|network.*(unreachable|error)|could not resolve/i, hint: 'Check your internet connection. If using IPFS, make sure the IPFS daemon is running.' },
  { pattern: /disk full|no space left/i, hint: 'Free up disk space on this computer and try again.' },
  { pattern: /timeout|timed out/i, hint: 'The operation timed out. Check that your device is still connected and responsive.' },
  { pattern: /heimdall.*not found|command not found.*heimdall/i, hint: 'Heimdall is not installed. Install it with your package manager (e.g. sudo apt install heimdall-flash).' },
  { pattern: /adb.*not found|command not found.*adb/i, hint: 'ADB is not installed. Install it with your package manager (e.g. sudo apt install adb).' },
  { pattern: /unauthorized/i, hint: 'Your device hasn\'t authorized this computer. Check the device screen for an authorization prompt and tap Allow.' },
  { pattern: /read-only file system/i, hint: 'The file system is read-only. If writing to the device, make sure it\'s in the correct mode (recovery/Download Mode).' },
  { pattern: /zip.*corrupt|bad.*crc|invalid.*zip/i, hint: 'The ZIP file appears corrupt. Try re-downloading it. If using IPFS, try the HTTP download instead.' },
  { pattern: /low battery|battery.*critical/i, hint: 'Battery is too low. Charge the device to at least 50% before flashing.' },
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
