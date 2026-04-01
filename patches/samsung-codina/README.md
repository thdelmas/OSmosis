# Samsung Galaxy Ace 2 (codina) — Mainline Linux Patches

Device tree patches to enable display and audio on the Samsung Galaxy Ace 2
(GT-I8160, codename "codina") running mainline Linux via postmarketOS.

## Background

The codina uses the ST-Ericsson NovaThor U8500 SoC. postmarketOS supports it
at the "testing" tier with a mainline kernel, but display and audio are broken
because the device tree is incomplete.

The sibling device Samsung Galaxy Xcover 2 (skomer, same SoC) has a working
display because it uses MIPI DSI — a more tested MCDE output path. The codina
uses DPI (parallel RGB) with SPI-GPIO for panel commands, which is a less
common configuration.

Audio is broken on **all** ux500 Samsung devices (codina, skomer, golden, etc.)
for the same reason: the MSP I2S nodes are disabled in every device tree.

## Patches

### 0001 — Display (DPI + WS2401 panel)

Enables the MCDE DPI output path and configures the SPI-GPIO-connected
WideChips WS2401 panel (Samsung LMS380KF01). Adds:

- MCDE DPI port + endpoint
- Panel power regulator (external Ricoh LDO on GPIO219)
- Panel reset/power sequencing
- KTD253 backlight enable

The panel variant (LMS380KF01 vs S6D27A1 on ~10% of units) is auto-detected
by U-Boot stemmy via the Samsung bootloader's `lcdtype` ATAG.

### 0002 — Audio (MSP I2S + AB8500 codec)

Enables the AB8500 audio codec and MSP I2S DAI controllers:

- MSP1 (primary audio path) with I2S pinctrl
- MSP3 (secondary audio path)
- AB8500 codec power supplies
- Sound card machine driver

This patch is applicable to **all** ux500 Samsung devices, not just codina.

## How to apply

These patches target the `linux-postmarketos-stericsson` kernel package in
pmaports. To apply:

```bash
# Clone pmaports
git clone https://gitlab.com/postmarketOS/pmaports.git
cd pmaports/device/community/linux-postmarketos-stericsson/

# Copy patches
cp /path/to/patches/*.patch .

# Add to APKBUILD source list and update checksums
# Then rebuild: pmbootstrap build linux-postmarketos-stericsson
```

Or use OSmosis to build a LETHE image that applies these patches automatically
during the pmOS build step.

## Hardware notes

- **SoC**: ST-Ericsson NovaThor U8500 (dual Cortex-A9 @ 800MHz)
- **RAM**: 768 MB
- **Storage**: 4 GB internal + microSD
- **Display**: 3.8" 480x800 TFT (WS2401 controller, DPI interface)
- **Audio**: AB8500 codec (headset, earpiece, speaker, mic)
- **Boot chain**: Samsung bootloader → U-Boot stemmy → mainline kernel
- **Flash tool**: Heimdall (Samsung Download Mode)
