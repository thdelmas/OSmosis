# FlashWizard

**Install any OS on any device.** CLI and web UI.

FlashWizard exists to give you real ownership of your hardware. Your device, your choice of operating system. Whether you're installing a privacy-respecting ROM on a phone, reviving an old tablet with a modern OS, or simply escaping a locked-down ecosystem — FlashWizard is here to help.

> We support Windows only so you can escape from it. We strongly recommend you don't stay there.

Currently focused on **Samsung devices via Heimdall** (Download Mode) and **custom ROM installs via `adb sideload`**. More platforms coming.

## Features

| # | Feature | CLI | Web |
|---|---------|:---:|:---:|
| 1 | Restore stock firmware (Heimdall) | x | x |
| 2 | Flash custom recovery (TWRP) | x | x |
| 3 | Sideload custom ROM (adb) | x | x |
| 4 | Sideload GApps / other ZIPs | x | x |
| 5 | Device presets & download | x | x |
| 6 | Auto-detect device (ADB) | x | x |
| 7 | Full workflow (restore + TWRP + ROM + GApps) | x | x |
| 8 | Backup partitions (boot, recovery, EFS) | x | x |
| 9 | Magisk boot.img patching | x | x |
| 10 | ROM update checker (SourceForge) | x | x |

Plus: SHA256 checksums, `--dry-run` mode, session logging, colored output, `--help`.

## Files

- `flash-wizard.sh` — CLI wizard (10 interactive options)
- `flash-wizard-web.sh` — Launcher for the web UI
- `web/` — Flask web app (dark theme dashboard, file browser, SSE streaming)
- `devices.cfg` — Device presets (SM-T805, SM-T800, SM-T705, SM-T700)
- `recover-sm-t805.sh` — One-shot SM-T805 recovery (reference)
- `bootloop-diagnose.sh` — Bootloop diagnostic via ADB/logcat

## Requirements

```bash
sudo apt update
sudo apt install heimdall-flash adb unzip wget -y
# Optional:
sudo apt install lz4 curl python3 python3-venv -y
```

## Usage — CLI

```bash
chmod +x flash-wizard.sh
./flash-wizard.sh            # interactive menu
./flash-wizard.sh --dry-run  # preview commands without executing
./flash-wizard.sh --help     # show help
```

The wizard will stop and ask you to perform any **physical steps** (enter Download Mode, boot recovery, start ADB sideload) before it runs commands.

## Usage — Web UI

```bash
chmod +x flash-wizard-web.sh
./flash-wizard-web.sh
```

This creates a Python venv, installs Flask, and opens `http://localhost:5000` in your browser. The web UI provides the same features as the CLI with a dark-themed dashboard, file browser, and real-time terminal output via SSE.

### Data directories

| Path | Contents |
|------|----------|
| `~/.flashwizard/logs/` | Session logs (one per run) |
| `~/.flashwizard/backups/` | Partition backups (timestamped) |
| `~/FlashWizard-downloads/` | Downloaded ROMs/firmware (per device) |

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

