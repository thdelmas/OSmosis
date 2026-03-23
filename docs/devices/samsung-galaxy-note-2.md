# Samsung Galaxy Note II (GT-N7100 / t03g)

## Device Info

| Field | Value |
|-------|-------|
| Brand | Samsung |
| Model | GT-N7100 |
| Codename | t03g |
| SoC | Exynos 4412 |
| Removable battery | Yes |
| TWRP codename | n7100 |
| Download Mode combo | Volume Down + Home + Power |
| Recovery Mode combo | Volume Up + Home + Power |

## Verified Installs

| OS | Recovery | Date | Status |
|----|----------|------|--------|
| **Replicant 6.0** | Replicant custom recovery | 2026-03-24 | Verified |

## Supported OS

- **Replicant** (6.0) — fully free/open Android (verified)
- **LineageOS** (14.1) — community Android
- **Stock Samsung** — restore via samfw.com

## Flash Methods

- **Recovery (Replicant)**: Flash Replicant's own recovery via Heimdall in Download Mode. Replicant ROMs require Replicant's own recovery — TWRP will not work.
- **ROM install**: ADB sideload via Replicant Recovery
- **Stock restore**: Heimdall or Odin

## Troubleshooting

### Device stuck in Download Mode loop

The Note II can get stuck repeatedly booting into Download Mode. Common causes:

**Sticky Home button** — The physical Home button triggers Download Mode when held during boot (Volume Down + Home + Power). If the button is stuck or gummed up with dust, the phone thinks you're pressing the Download Mode combo.

Fix:
1. Unplug USB
2. Remove the back cover and battery
3. Press the Home button firmly several times to unstick it
4. Clean around the button edges with compressed air or a thin cloth
5. Reinsert the battery
6. Boot without pressing any buttons — just press Power briefly
7. Only plug USB in after you see the home screen or recovery

**USB cable triggering reboot** — Some Samsung devices re-enter Download Mode when USB is connected during boot. The cable provides power which can interfere with the boot process.

Fix:
1. Always unplug USB before rebooting
2. Let the device fully boot before plugging USB back in
3. If booting into recovery: hold Volume Up + Home + Power with USB unplugged, plug in only after TWRP loads

**Battery pull required** — Pressing and holding Power does not always force a restart on the Note II when it's in Download Mode. The only reliable way to force a restart is to remove the battery.

Fix:
1. Unplug USB
2. Remove the battery
3. Wait 15 seconds
4. Reinsert battery
5. Immediately hold Volume Up + Home + Power for recovery, or just press Power for normal boot

### Heimdall "Protocol initialisation failed"

The Download Mode session goes stale after one Heimdall command, or after the phone has been in Download Mode for too long.

Fix:
1. Unplug USB
2. Pull the battery, wait 15 seconds, reinsert
3. Re-enter Download Mode (Volume Down + Home + Power)
4. Plug USB in
5. Run the Heimdall command immediately — the session is only valid for one operation

### TWRP flash succeeds but device doesn't boot into TWRP

After flashing TWRP via Heimdall, the device may reboot back into Download Mode instead of normal boot or recovery.

Fix:
1. Unplug USB
2. Pull the battery
3. Reinsert battery
4. Hold Volume Up + Home + Power to boot into TWRP
5. Do not plug USB until TWRP is fully loaded

### ADB sideload "signature verification failed"

Stock Samsung recovery rejects unsigned ROMs. This is expected — custom ROMs require TWRP.

Fix:
1. Install TWRP first (see Flash Methods above)
2. Boot into TWRP
3. Go to Advanced > ADB Sideload > Swipe to start
4. Retry the sideload

### Replicant ROM download appears corrupted

The Replicant download server may serve incomplete files. Verify the download:
- Check file size (should be ~200MB+)
- Verify SHA256 checksum against the Replicant images page
- Re-download if the file is not a valid ZIP

## Notes

- The Note II uses USB product ID `04e8:685d` in Download Mode — this is shared across many Samsung devices, so OSmosis cannot auto-detect the exact model from USB alone
- Replicant ROMs require Replicant's own recovery — do not use TWRP for Replicant installs
- TWRP uses codename `n7100` (not `t03g`) for downloads, but is only needed for non-Replicant ROMs (e.g. LineageOS)
- The TWRP download server (dl.twrp.me) requires a Referer header to serve the actual .img file
- Heimdall sessions become stale after one command on this device — plan operations carefully
