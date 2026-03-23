# Samsung Devices — Common Troubleshooting

This document covers issues common to Samsung Galaxy phones and tablets that use Download Mode and Heimdall/Odin for flashing.

## Boot Modes

| Mode | Button combo | USB shows as |
|------|-------------|--------------|
| Download Mode | Volume Down + Home + Power (older) or Volume Down + Bixby + Power | `04e8:685d` or similar |
| Recovery Mode | Volume Up + Home + Power (older) or Volume Up + Bixby + Power | ADB `recovery` or `sideload` |
| Normal boot | Power only | ADB `device` |

On newer Samsung devices without a Home button, replace Home with Bixby or Side button. On devices with no physical buttons, use `adb reboot download` or `adb reboot recovery`.

## Download Mode issues

### Stuck in Download Mode loop

**Symptoms**: Device boots into Download Mode every time, even after battery pull.

**Causes** (most common first):
1. **Sticky Home/Bixby button** — physically stuck, triggering the Download Mode combo
2. **USB cable connected during boot** — power from USB can trigger Download Mode
3. **Corrupted boot partition** — device can't find a valid kernel
4. **Odin/Heimdall left device in a bad state**

**Fix sequence** (try in order):
1. Unplug USB, pull battery (if removable), wait 15s
2. Press Home/Bixby button firmly several times to unstick
3. Reinsert battery, boot with Power only (no other buttons)
4. If still looping: try Recovery Mode (Volume Up combo) instead of normal boot
5. If Recovery Mode works: flash a ROM from there to fix boot partition
6. If nothing works: flash stock firmware via Heimdall to restore all partitions

### Heimdall "Protocol initialisation failed"

**Cause**: The Heimdall protocol session has gone stale. This happens when:
- The phone has been in Download Mode too long
- A previous Heimdall command was run and the session wasn't reset
- USB connection was interrupted

**Fix**: Battery pull + fresh Download Mode entry + immediate command:
1. Unplug USB
2. Pull battery, wait 15s, reinsert
3. Enter Download Mode (Volume Down combo)
4. Plug USB
5. Run the Heimdall command within seconds — don't run `heimdall detect` first, go straight to the flash command

### Heimdall "Claiming interface" / permission denied

**Cause**: Linux udev rules don't grant USB access to the current user.

**Fix**: Run `sudo bash scripts/setup-udev.sh` once, then unplug and replug the device.

## Recovery Mode issues

### ADB sideload "signature verification failed"

**Cause**: Stock Samsung recovery only accepts manufacturer-signed OTA updates. Custom ROMs are not signed by Samsung.

**Fix**: Install TWRP custom recovery first, then sideload from TWRP.

### TWRP not appearing after flash

**Cause**: Samsung's auto-reboot after Heimdall flash may go back to Download Mode or normal boot instead of recovery.

**Fix**: Manual boot into recovery after flash:
1. After Heimdall reports success, unplug USB
2. Battery pull if needed to exit Download Mode
3. Hold Volume Up + Home + Power (recovery combo)
4. TWRP should appear
5. Plug USB only after TWRP is fully loaded

### TWRP asks to keep system read-only / modify partition

When TWRP boots for the first time, it may ask whether to modify the system partition. For installing a custom ROM, swipe to allow modifications.

## General Samsung tips

- **Always unplug USB before rebooting** between modes
- **Battery pull is the most reliable reset** on devices with removable batteries
- **One Heimdall command per session** — on older devices, the Download Mode protocol session goes stale after the first command
- **USB product ID `04e8:685d`** is shared across many Samsung models in Download Mode — don't rely on it for model identification
- **TWRP codenames may differ** from the device codename (e.g., device `t03g` but TWRP uses `n7100`)
