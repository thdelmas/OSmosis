# Osmosis

**Install any OS on any device.** CLI and web UI.

Osmosis exists to give you real ownership of your hardware. Your device, your choice of operating system. Whether you're installing a privacy-respecting ROM on a phone, reviving an old tablet with a modern OS, or simply escaping a locked-down ecosystem — Osmosis is here to help.

> We support Windows only so you can escape from it. We strongly recommend you don't stay there.

Read the **[Manifesto](MANIFESTO.md)** — the seven principles behind Osmosis.

Currently focused on **Samsung devices via Heimdall** (Download Mode) and **custom ROM installs via `adb sideload`**. More platforms coming.

## Supported & target device types

Osmosis's goal is to cover **any device you can reflash**. Here's the landscape:

### Phones & tablets

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Samsung Galaxy (Exynos) | Samsung Android / One UI | LineageOS, /e/OS, CalyxOS, PostmarketOS | Heimdall (Download Mode) | **Supported** |
| Samsung Galaxy (Snapdragon) | Samsung Android / One UI | LineageOS, /e/OS | Odin / Heimdall | Planned |
| Google Pixel | Pixel Android | CalyxOS, GrapheneOS, LineageOS | fastboot | Planned |
| OnePlus | OxygenOS | LineageOS, /e/OS, Paranoid Android | fastboot | Planned |
| Xiaomi | MIUI / HyperOS | LineageOS, /e/OS, Pixel Experience | fastboot (unlocked BL) | Planned |
| Fairphone | Fairphone OS | /e/OS, LineageOS, CalyxOS | fastboot | Planned |
| PinePhone / PineTab | Various Linux | PostmarketOS, Mobian, Manjaro ARM, UBports | SD card / Tow-Boot | Planned |
| Librem 5 | PureOS | Mobian, PostmarketOS | uuu / SD card | Planned |

### Single-board computers & DIY

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Raspberry Pi | Raspberry Pi OS | Ubuntu, Fedora, LibreELEC, Home Assistant | SD card / rpiboot | Planned |
| Orange Pi / Banana Pi | Armbian | Ubuntu, Debian, DietPi | SD card / USB | Planned |
| NVIDIA Jetson | JetPack / L4T | Ubuntu, Yocto | sdkmanager / flash.sh | Planned |
| BeagleBone | Debian | Yocto, Buildroot, FreeBSD | SD card / USB DFU | Planned |
| ESP32 / Arduino | None | MicroPython, ESPHome, Tasmota | esptool / serial | Planned |

### Cars & automotive

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Tesla MCU | Tesla firmware | Custom Linux (research) | OTA / USB (limited) | Research |
| Android Auto head units | Android (locked) | LineageOS, custom AOSP | fastboot / scatter | Planned |
| Raspberry Pi car setups | N/A | OpenAuto Pro, Crankshaft, Android Auto | SD card | Planned |
| OBD2 / ECU tuning | Vendor firmware | Open-source tunes | CAN bus / J2534 | Research |

### GPS & navigation

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Garmin handheld / auto | Garmin OS | Custom maps / firmware mods | USB mass storage | Planned |
| TomTom | TomTom NavCore | OpenTom (legacy) | USB / SD card | Planned |
| Marine chartplotters | Vendor firmware | OpenCPN (on compatible hw) | SD card / USB | Research |
| Drone controllers (DJI) | DJI firmware | Custom FW (research) | DUMLdore / USB | Research |

### Marine & boats

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Raymarine / Garmin MFD | Vendor firmware | Firmware updates / mods | SD card / network | Research |
| NMEA 2000 devices | Vendor firmware | SignalK (on RPi gateway) | CAN bus / serial | Planned |
| Boat Raspberry Pi hubs | Various | OpenPlotter, SignalK, OpenCPN | SD card | Planned |
| AIS transponders | Vendor firmware | dAISy / custom (open hw) | Serial / USB | Research |

### Routers, NAS & networking

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Consumer routers | Vendor firmware | OpenWrt, DD-WRT, FreshTomato | TFTP / web UI / serial | Planned |
| Synology / QNAP NAS | DSM / QTS | XPEnology, TrueNAS (on x86) | USB / bootloader | Planned |
| Managed switches | Vendor OS | OpenSwitch, SONiC | Serial / ONIE | Research |

### Game consoles & media

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Nintendo Switch | HOS | Atmosphere (CFW), Ubuntu, Android | RCM / Hekate | Planned |
| Steam Deck | SteamOS | HoloISO, Bazzite, Windows | USB / SD | Planned |
| PS Vita | Sony firmware | HENkaku / Enso (CFW) | USB / FTP | Research |
| Chromecast / Fire TV | Vendor Android | LineageOS (some models) | fastboot / adb | Planned |
| Kindle | Fire OS | LineageOS (Fire tablets) | adb sideload / fastboot | Planned |

### Electric scooters & PEVs

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| Ninebot Max G30/G2/F2 | Ninebot firmware | SHFW, CFW (cfw.sh) | BLE OTA / ST-Link | **Supported** |
| Ninebot ESx/Ex series | Ninebot firmware | SHFW, CFW (esx.cfw.sh) | BLE OTA / ST-Link | **Supported** |
| Ninebot F/D series | Ninebot firmware | SHFW, CFW | BLE OTA / ST-Link | **Supported** |
| Ninebot G3/F3/GT3/ZT3 | Ninebot firmware | Pending SHFW | BLE OTA / ST-Link | Planned |
| Ninebot P65/P100S/GT1/GT2 | Segway firmware | Pending | BLE OTA / ST-Link | Planned |
| Xiaomi M365/Pro/1S/Pro2/3 | Xiaomi firmware | SHFW, CFW (mi.cfw.sh) | BLE OTA / ST-Link | **Supported** |
| Xiaomi Mi 4/4 Pro/4 Ultra | Xiaomi firmware | CFW (bw-patcher) | UART / ST-Link | **Supported** |
| Xiaomi Mi 5/5 Pro | Xiaomi firmware | Stock only (DFU verify fails) | UART | Research |
| Okai ES series | Okai firmware | Community R&D | ST-Link | Research |

### Wearables & IoT

| Device type | Stock OS | Alternative OS | Flash method | Status |
|-------------|----------|----------------|--------------|--------|
| PineTime | InfiniTime | Wasp-OS, custom | OTA BLE / SWD | Planned |
| ESP-based smart home | Vendor cloud FW | Tasmota, ESPHome, WLED | esptool / OTA | Planned |
| IP cameras | Vendor firmware | OpenIPC, Dafang Hacks | SD card / UART | Planned |
| Smart speakers (rooted) | Vendor OS | Custom (limited) | ADB / UART | Research |

### Legend

- **Supported** — works today in Osmosis
- **Planned** — on the roadmap, flash method is well-documented
- **Research** — feasible but requires reverse engineering or device-specific tooling

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
| 11 | Create bootable USB/SD card (dd) | x | x |
| 12 | PXE boot server (dnsmasq/TFTP) | x | x |
| 13 | Scan for scooters (Bluetooth) | x | x |
| 14 | Flash scooter firmware (BLE/ST-Link) | x | x |
| 15 | Read scooter info | x | x |

Plus: SHA256 checksums, `--dry-run` mode, session logging, colored output, `--help`.

### Electric scooter support

Osmosis supports flashing custom firmware on Xiaomi and Ninebot electric scooters via Bluetooth Low Energy (BLE) or ST-Link. Supported operations:

- **BLE scan** — discover nearby scooters over Bluetooth
- **Read info** — serial number, firmware versions (DRV/BLE/BMS/MCU/VCU), UID
- **Flash CFW/SHFW** — install ScooterHacking firmware or custom firmware over BLE
- **ST-Link flash** — hardware-level flashing for recovery or restricted controllers
- **Stock restore** — roll back to original Ninebot/Xiaomi firmware

Supported scooter families: Ninebot Max (G30/G2/G3), Ninebot F/D/E/P/GT series, Xiaomi M365/Pro/1S/Pro2/Mi4/Mi5, Okai, and more. See `scooters.cfg` for the full list.

Protocol implementation based on community research: [ninebot-docs](https://github.com/etransport/ninebot-docs/wiki/protocol), [M365-BLE-PROTOCOL](https://github.com/CamiAlfa/M365-BLE-PROTOCOL), and the [ScooterHacking](https://scooterhacking.org) community.

## Files

- `osmosis.sh` — CLI wizard (15 interactive options)
- `osmosis-web.sh` — Launcher for the web UI
- `web/` — Flask web app (dark theme dashboard, file browser, SSE streaming)
- `web/scooter_proto.py` — Ninebot/Xiaomi BLE protocol and DFU implementation
- `web/routes/scooter.py` — Scooter API routes (scan, info, flash)
- `devices.cfg` — Phone/tablet device presets (Samsung Galaxy Tab S family)
- `scooters.cfg` — Electric scooter presets (50+ models with CFW URLs and flash methods)
- `recover-sm-t805.sh` — One-shot SM-T805 recovery (reference)
- `bootloop-diagnose.sh` — Bootloop diagnostic via ADB/logcat

## Requirements

```bash
sudo apt update
sudo apt install heimdall-flash adb unzip wget -y
# Optional:
sudo apt install lz4 curl python3 python3-venv -y
# For scooter flashing (BLE):
pip install bleak
# For scooter flashing (ST-Link):
sudo apt install stlink-tools -y
# For PXE boot server:
sudo apt install dnsmasq pxelinux syslinux-common -y
```

## Usage — CLI

```bash
chmod +x osmosis.sh
./osmosis.sh            # interactive menu
./osmosis.sh --dry-run  # preview commands without executing
./osmosis.sh --help     # show help
```

The wizard will stop and ask you to perform any **physical steps** (enter Download Mode, boot recovery, start ADB sideload) before it runs commands.

## Usage — Web UI

```bash
chmod +x osmosis-web.sh
./osmosis-web.sh
```

This creates a Python venv, installs Flask, and opens `http://localhost:5000` in your browser. The web UI provides the same features as the CLI with a dark-themed dashboard, file browser, and real-time terminal output via SSE.

### Data directories

| Path | Contents |
|------|----------|
| `~/.osmosis/logs/` | Session logs (one per run) |
| `~/.osmosis/backups/` | Partition backups (timestamped) |
| `~/Osmosis-downloads/` | Downloaded ROMs/firmware (per device) |

### Device presets via `devices.cfg`

`osmosis.sh` looks for `devices.cfg` next to the script. Each non-comment line defines one device:

```text
# id|label|model|codename|rom_url|twrp_url|eos_url|stock_fw_url|gapps_url
sm-t805|Galaxy Tab S 10.5 LTE|SM-T805|chagalllte|https://sourceforge.net/projects/exynos5420/files/Lineage-18.1/chagalllte/lineage-18.1-20230312-UNOFFICIAL-chagalllte.zip/download|https://dl.twrp.me/chagalllte/twrp-3.6.2_9-0-chagalllte.img.tar|https://sourceforge.net/projects/eosbuildsronnz98/files/Samsung/Samsung%20Galaxy%20Tab%20S/e-2.3-r-20251027-UNOFFICIAL-chagalllte.zip/download|https://samfw.com/firmware/SM-T805||
```

In the wizard, choose option **5** (“Use device presets from devices.cfg”) to:

- Select a device preset
- Choose a target directory
- Interactively download any of: stock firmware, TWRP, LineageOS ROM, /e/OS ROM, GApps (for LOS, not /e/OS)

## Useful download links

Device-specific download links and references are maintained in the [`docs/`](docs/) directory:

- [SM-T805 / chagalllte (Galaxy Tab S 10.5 LTE)](docs/links-sm-t805.md)

See [`docs/README.md`](docs/README.md) for the full index.

