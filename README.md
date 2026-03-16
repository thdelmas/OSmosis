# FlashWizard

Interactive, command-line helper for flashing and recovery workflows.

Currently focused on **Samsung devices via Heimdall** (Download Mode) and **custom ROM installs via `adb sideload`**.

## Scripts

- `flash-wizard.sh`: interactive wizard for:
  - restoring stock firmware from a Samsung firmware ZIP (BL/AP/CP/CSC `.tar.md5`)
  - flashing a custom recovery image (`.img`) via Heimdall
  - sideloading a ROM ZIP (TWRP / custom recovery)
  - sideloading GApps / other ZIPs
  - using presets from `devices.cfg` to auto-download ROM / recovery / firmware files
- `recover-sm-t805.sh`: one-shot recovery helper that was used to rescue an SM‑T805 (kept for reference)
- `bootloop-diagnose.sh`: local helper (if present) for bootloop diagnostics
 - `devices.cfg`: simple config file listing device presets and download URLs

## Requirements

Ubuntu/Debian packages:

```bash
sudo apt update
sudo apt install heimdall-flash adb unzip -y
```

## Usage

```bash
chmod +x flash-wizard.sh
./flash-wizard.sh
```

The wizard will stop and ask you to perform any **physical steps** (enter Download Mode, boot recovery, start ADB sideload) before it runs commands.

### Device presets via `devices.cfg`

`flash-wizard.sh` looks for `devices.cfg` next to the script. Each non-comment line defines one device:

```text
# id|label|model|codename|rom_url|twrp_url|eos_url|stock_fw_url|gapps_url
sm-t805|Galaxy Tab S 10.5 LTE|SM-T805|chagalllte|https://sourceforge.net/projects/exynos5420/files/Lineage-18.1/chagalllte/lineage-18.1-20230312-UNOFFICIAL-chagalllte.zip/download|https://dl.twrp.me/chagalllte/twrp-3.6.2_9-0-chagalllte.img.tar|https://sourceforge.net/projects/eosbuildsronnz98/files/Samsung/Samsung%20Galaxy%20Tab%20S/e-2.3-r-20251027-UNOFFICIAL-chagalllte.zip/download|https://samfw.com/firmware/SM-T805||
```

In the wizard, choose option **5** (“Use device presets from devices.cfg”) to:

- Select a device preset
- Choose a target directory
- Interactively download any of: stock firmware, TWRP, LineageOS ROM, /e/OS ROM, GApps (for LOS, not /e/OS)

## Useful download links (SM‑T805 / chagalllte)

These are the URLs the wizard assumes for your Galaxy Tab S 10.5 LTE:

- **Stock Samsung firmware (Android 6.0.1)**  
  - SamFw firmware page for `SM-T805`:  
    - `https://samfw.com/firmware/SM-T805`
- **LineageOS 18.1 (Android 11, unofficial)**  
  - XDA thread:  
    - `https://xdaforums.com/t/rom-unofficial-11-lineageos-18-1-for-samsung-galaxy-tab-s-10-5-sm-t805-chagalllte-beta.4512951/`  
  - SourceForge builds (chagalllte):  
    - `https://sourceforge.net/projects/exynos5420/files/Lineage-18.1/chagalllte/`
- **/e/OS‑R (Android 11, LOS 18.1‑based, unofficial)**  
  - XDA thread:  
    - `https://xdaforums.com/t/rom-unofficial-11-r-e-os-r-lineageos-18-1-based-for-samsung-galaxy-tab-s-sm-t700-sm-t705-sm-t800-sm-t805-sm-p600.4651583/`  
  - Latest chagalllte build (used by option 5 in `flash-wizard.sh`):  
    - `https://sourceforge.net/projects/eosbuildsronnz98/files/Samsung/Samsung%20Galaxy%20Tab%20S/e-2.3-r-20251027-UNOFFICIAL-chagalllte.zip/download`
- **TWRP recovery for SM‑T805 (chagalllte)**  
  - Download index:  
    - `https://dl.twrp.me/chagalllte/`
- **MindTheGapps (Android 11, ARM)** – for LineageOS (not for /e/OS)  
  - MindTheGapps releases:  
    - `https://mindthegapps.magisk.dev/`  
  - Example file often used:  
    - `MindTheGapps-11.0.0-arm-20220217_095902.zip`

