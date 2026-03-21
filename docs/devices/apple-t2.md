# Apple T2 Macs

OSmosis supports backup, restore, and diagnostics for the Apple T2 Security Chip found in Mac models from 2018 to 2020. The T2 chip handles SSD encryption, secure boot, Touch ID, audio processing, and the system management controller (SMC).

---

## What is the T2 Chip?

The Apple T2 is a custom ARM-based security chip (based on the Apple A10) that acts as a co-processor in Intel Macs. It handles:

- **SSD encryption:** All data on the internal SSD is encrypted by the T2. The SSD cannot be read without the T2.
- **Secure Boot:** Verifies the macOS boot chain. Can be configured to Full Security, Medium Security, or No Security.
- **Touch ID:** Processes fingerprint data in a Secure Enclave.
- **Audio:** Handles microphone and speaker processing.
- **SMC:** System Management Controller (fan control, power management, keyboard backlight).
- **Image signal processor:** Processes FaceTime camera data.

---

## Supported Devices

### MacBook Pro

| Device | Model Identifier | Board ID | Years | Notes |
|--------|-----------------|----------|-------|-------|
| MacBook Pro 13" (2018) | MacBookPro15,2 | J132 | 2018 | Touch Bar, 4 Thunderbolt 3 |
| MacBook Pro 15" (2018) | MacBookPro15,1 | J680 | 2018 | Touch Bar, 6-core |
| MacBook Pro 13" (2019) | MacBookPro15,4 | J213 | 2019 | Touch Bar, 2 Thunderbolt 3 |
| MacBook Pro 15" (2019) | MacBookPro15,3 | J780 | 2019 | Touch Bar, 8-core |
| MacBook Pro 16" (2019) | MacBookPro16,1 | J152F | 2019 | Touch Bar, first 16-inch model |
| MacBook Pro 13" (2020, 2-port) | MacBookPro16,3 | J214K | 2020 | Touch Bar, 2 Thunderbolt 3 |
| MacBook Pro 13" (2020, 4-port) | MacBookPro16,2 | J223 | 2020 | Touch Bar, 4 Thunderbolt 3 |

### MacBook Air

| Device | Model Identifier | Board ID | Years | Notes |
|--------|-----------------|----------|-------|-------|
| MacBook Air (2018) | MacBookAir8,1 | J140K | 2018 | Retina display, Touch ID |
| MacBook Air (2019) | MacBookAir8,2 | J140A | 2019 | True Tone display |
| MacBook Air (2020) | MacBookAir9,1 | J230K | 2020 | Scissor keyboard |

### Desktop Macs

| Device | Model Identifier | Board ID | Notes |
|--------|-----------------|----------|-------|
| iMac 27" (2020) | iMac20,1 | J185 | 5K Retina, 10th-gen Intel |
| iMac 27" (2019) | iMac19,1 | J160 | 5K Retina, 9th-gen Intel |
| iMac Pro (2017) | iMacPro1,1 | J137 | First Mac with T2 chip |
| Mac Pro (2019) | MacPro7,1 | J160 | Tower / rack configuration |
| Mac mini (2018) | Macmini8,1 | J174 | Space Gray, 4 Thunderbolt 3 |

---

## OSmosis T2 Operations

### Backup

OSmosis can back up the T2 chip's BridgeOS firmware and configuration. This is critical before any restore or troubleshooting operation.

### Restore

If the T2 chip becomes unresponsive or corrupted (e.g., after a failed macOS update or power loss during firmware update), OSmosis can restore BridgeOS using Apple's DFU (Device Firmware Upgrade) mode.

### DFU Mode

DFU mode is how the T2 chip accepts firmware updates. To enter DFU mode:

**MacBook Pro / MacBook Air:**
1. Shut down the Mac completely
2. Press and hold the power button (Touch ID) for 10 seconds, then release
3. Wait 3 seconds
4. Press and hold all three: **Right Shift + Left Option + Left Control** and the **power button** for 10 seconds
5. Release the keys but keep holding the power button for 10 more seconds
6. Connect a USB-C cable from a second Mac (or a computer running OSmosis)

**Desktop Macs (iMac, Mac Pro, Mac mini):**
1. Disconnect all power and peripherals
2. For iMac: connect USB-C cable to the Thunderbolt port closest to the Ethernet port
3. For Mac mini: connect USB-C cable to the Thunderbolt port closest to the HDMI port
4. For Mac Pro: connect USB-C cable to the Thunderbolt port closest to the power connector
5. Connect power while holding the power button
6. Release after 3 seconds

### BridgeOS

BridgeOS is the operating system running on the T2 chip. It is based on a variant of iOS/watchOS. Apple publishes BridgeOS updates as part of macOS updates and through the [Apple support page](https://support.apple.com/en-us/106337).

---

## Secure Boot Settings

The T2 chip's Secure Boot can be configured in macOS Recovery (Command+R at boot):

| Setting | Description |
|---------|-------------|
| **Full Security** | Default. Only the latest, signed macOS can boot. Verified against Apple's servers. |
| **Medium Security** | Allows booting older signed macOS versions. Does not verify with Apple's servers. |
| **No Security** | Allows booting any OS, including Linux. Required for Linux dual-boot. |

### External Boot

By default, the T2 blocks booting from external media (USB drives, Thunderbolt drives). To allow external boot:

1. Boot to macOS Recovery (Command+R)
2. Open **Startup Security Utility** from the Utilities menu
3. Set **Allowed Boot Media** to "Allow booting from external or removable media"

---

## Running Linux on T2 Macs

The [T2 Linux project](https://t2linux.org/) provides kernel patches and drivers for running Linux on T2 Macs. Requirements:

1. Set Secure Boot to **No Security**
2. Enable **External Boot**
3. Install a T2-patched Linux kernel (standard kernels lack T2 audio, keyboard, touchpad, and WiFi drivers)

**Supported distributions with T2 patches:**
- Ubuntu (via t2linux PPA)
- Fedora (via t2linux COPR)
- Arch Linux (via t2linux packages)
- Manjaro (community builds)

**What works with T2 Linux patches:**
- Internal keyboard and trackpad
- Touch Bar (basic display, function keys)
- Audio (speakers and headphone jack)
- WiFi (with firmware from macOS)
- Thunderbolt
- Screen brightness

**What has limitations:**
- Touch ID (not supported — T2 Secure Enclave does not expose fingerprint data to Linux)
- Fan control (works via `t2fanrd` daemon)

---

## Identifying Your Mac

To check if your Mac has a T2 chip:

1. Click the Apple menu > **About This Mac**
2. Click **System Report**
3. In the sidebar, select **Controller** (under Hardware)
4. If you see "Apple T2 Security Chip", your Mac has T2

Alternatively, from Terminal:
```
system_profiler SPiBridgeDataType
```

If this returns T2 chip information, you have a T2 Mac.

---

## Important Notes

- **SSD encryption is always on.** The T2 encrypts all internal SSD data. If the T2 chip fails and cannot be restored, the data on the SSD is unrecoverable.
- **Back up regularly.** Time Machine or other backups are essential with T2 Macs.
- **Do not interrupt firmware updates.** A power loss during a BridgeOS or macOS update can corrupt the T2, requiring DFU restore.
- **Apple Silicon Macs (M1/M2/M3/M4) do not have a T2 chip.** They integrate equivalent functionality directly into the main SoC. OSmosis's T2 support applies only to Intel Macs from 2017-2020.
