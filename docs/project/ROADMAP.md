# Osmosis Roadmap

From flashing tool to device freedom platform.

This roadmap is organized into phases. Each phase builds on the previous one
and delivers standalone value. Phases are not strictly sequential — work can
overlap where dependencies allow.

---

## Phase 0 — Foundations (current state)

What Osmosis already does well:

- [x] Samsung Heimdall flashing (stock, recovery, partitions)
- [x] ADB sideload (custom ROMs, GApps, mods)
- [x] Guided wizard (step-by-step, 9 device categories)
- [x] Scooter BLE flashing (Ninebot/Xiaomi, 40+ models)
- [x] Scooter ST-Link flashing (hardware recovery)
- [x] ROM discovery (LineageOS, /e/OS, TWRP, postmarketOS, Replicant)
- [x] IPFS ROM distribution
- [x] Bootable USB/SD creation
- [x] PXE boot server
- [x] Device auto-detection (ADB + USB VID)
- [x] Partition backup with SHA256 verification
- [x] Magisk boot.img patching
- [x] Dry-run mode, session logging, i18n
- [x] Web UI + CLI with feature parity

---

## Phase 1 — Safety Net (done)

*"If it can go wrong, we should have a guide for it."*

### 1.0 Hardware Expansion Housekeeping

- [ ] Add USB VID/PID entries for new vendors to the detection registry
- [ ] Add i18n strings for new device labels and categories
- [ ] Handle `support_status: not-supported` in the UI for locked systems
- [ ] Add device category grouping in the wizard for new families
- [ ] Stub documentation pages in `docs/devices/`

### 1.1 Recovery & Unbrick Documentation

- [x] Per-device-category recovery guides (Samsung, Scooter, Pixel, Bootable)
- [x] "What went wrong?" troubleshooting wizard (`StepTroubleshoot.vue`)
- [x] Pre-flash checklist (`PagePreflight.vue`, phone/scooter/pixel checks)

### 1.2 Firmware Verification & Archive

- [x] SHA256 hash registry of every flashed firmware (`web/registry.py`)
- [x] Pre-flash verification integrated into all flash routes
- [x] IPFS firmware archive with version history and downgrade
- [x] Signed manifest sharing for verified firmware
- [x] Firmware downgrade via `POST /api/registry/restore`

### 1.3 Enhanced Backup

- [x] Full NAND backup for Samsung (`POST /api/backup/full`)
- [x] Scooter firmware backup before flash (`POST /api/scooter/backup`)
- [x] One-click rollback (`POST /api/backup/restore`)
- [x] IPFS backup sync (`POST /api/backup/ipfs-sync`)

---

## Phase 2 — CFW Builder (done)

*"Don't just flash what others built — build your own."*

### 2.1 Scooter CFW Builder (Web UI)

- [x] Per-model patch builder with toggleable patches and safe defaults
- [x] Parameter validation with safety warnings
- [x] Save/load/share configurations (JSON export/import + IPFS manifests)
- [x] Generate firmware ZIP, preview byte-level diff
- [x] Auto-pin to IPFS after build

### 2.2 E-Bike Support

- [x] Per-controller flash/detect/backup via ST-Link (`web/routes/ebike.py`)
- [x] Wizard step for e-bike operations (`StepEbike.vue`)

### 2.3 Phone ROM Customization

- [x] Post-install debloat via ADB (`POST /api/configure-rom`)
- [x] Privacy hardening presets (analytics, location, backup)
- [x] Display settings (dark mode, font scale)
- [x] Locale and timezone configuration

### 2.4 Router/IoT Firmware Customization

- [ ] OpenWrt package selection UI (future)
- [ ] First-boot script editor (future)

---

## Phase 3 — Live Device Dashboard (done)

*"The flash is just the beginning."*

### 3.1 Scooter Live Dashboard

- [x] Real-time telemetry over BLE (speed, battery, voltage, current,
  temperature, odometer, trip, uptime, error codes, speed mode, lock status)
- [x] SSE streaming endpoint (`GET /api/scooter/telemetry-stream/<address>`)
- [x] Register read/write for supported parameters (`POST /api/scooter/register/write`)
- [x] Speed profile switching, lock/unlock, tail light from dashboard
- [x] Web UI with live-updating gauges and quick action buttons

### 3.2 Phone Device Monitor

- [x] Post-flash health check via ADB (`POST /api/device-info`)
- [x] Installed ROM version, root/Magisk status, battery, storage

### 3.3 IoT Device Dashboard

- [ ] ESP device status via MQTT or HTTP (future)
- [ ] OTA trigger from dashboard (future)

---

## Phase 4 — OTA Updates (done)

*"Flash once, update forever."*

### 4.1 Scooter OTA

- [x] Check for CFW updates over BLE (`POST /api/scooter/ota/check`)
- [x] One-click OTA apply with backup (`POST /api/scooter/ota/apply`)
- [x] Supports IPFS, upstream URL, and registry sources
- [ ] Delta patch support (future)
- [ ] Update channel selection (future)

### 4.2 Phone Update Pipeline

- [x] ROM update checker (`GET /api/updates`)
- [x] One-click update with backup (`POST /api/update-rom`: preflight ->
  backup -> download (IPFS-first) -> verify -> sideload)
- [x] Companion Termux script with ROM update checker

### 4.3 ESP/IoT OTA (future)

- [ ] Push firmware over Wi-Fi
- [ ] Multi-device fleet updates

---

## Phase 5 — Device Database & Community (done)

*"If it has a chip and a flash method, it belongs here."*

### 5.1 Searchable Device Database

- [x] Device search API (`GET /api/devices/search?q=...`)
- [x] Community links per device (`GET /api/community/<codename>`)
- [x] Wiki integration (LineageOS, postmarketOS, XDA, iFixit, GSMArena)
- [x] YAML config migration (`POST /api/devices/migrate-yaml`) — YAML
  preferred, .cfg fallback

### 5.2 Community Contributions

- [x] Device submission API (`POST /api/devices/submit`) with review queue
- [x] Submission approval flow (`POST /api/devices/submissions/approve`)
- [x] Signed IPFS manifests for firmware/CFW sharing
- [x] Config channel subscriptions for community device databases
- [x] Trusted publisher system (Ed25519 signatures)

### 5.3 Community Wiki

- [x] Wiki search integration (`PageWiki.vue`)
- [ ] Standalone wiki deployment (future)

---

## Phase 6 — New Device Families

*"Every platform, every form factor."*

Goal: expand beyond Samsung phones and scooters to deliver on the manifesto's
promise. Device presets for many of these families already exist in the config
files — this phase is about building the flash/monitor workflows around them.

### 6.1 fastboot Devices (done)

- [x] Generic fastboot flash workflow (unlock -> flash -> relock)
- [x] Per-OEM bootloader unlock guidance (Google, OnePlus, Xiaomi, Samsung,
  Fairphone, Motorola) via `GET /api/fastboot/unlock-guide`
- [x] Factory image flash (flash-all.sh + individual partition fallback)
- [x] Custom ROM flash with vbmeta verification disable
- [x] Bootloader lock/unlock endpoints
- [ ] Anti-rollback index (ARI) validation (future)
- [ ] AVB key management for relocking after custom ROM (future)

### 6.2 Linux-Native Phones & Tablets

Presets added: PinePhone, PinePhone Pro, PineTab 2, Librem 5.

- [ ] Tow-Boot / U-Boot bootloader flashing
- [ ] postmarketOS, Mobian, Manjaro ARM as flash targets
- [ ] SD card vs. eMMC install workflows
- [ ] Jumpdrive utility integration for eMMC access

### 6.3 ESP32 / IoT

Presets added: ESP32-C2, LILYGO T-Display/T-Display S3, M5Stack Core2/
CoreS3/ATOM Lite/AtomS3/Stamp C3.

- [ ] esptool integration for serial flashing
- [ ] Browser-based flashing via Web Serial API (ESP Web Tools pattern)
- [ ] Tasmota and ESPHome as first-class flash targets
- [ ] Chipset auto-detection (ESP8266 vs ESP32 vs S2/S3/C2/C3/C6/H2)
- [ ] Partition table awareness (factory, OTA_0, OTA_1, NVS)

### 6.4 LoRa / Meshtastic Devices

Presets added: LILYGO T-Beam/T-Beam S3/T-Echo, Heltec V3/Wireless Tracker,
RAK WisBlock 4631/11200.

- [ ] Meshtastic firmware as a first-class flash target
- [ ] LoRa frequency band selection by region (EU868, US915, AU915, etc.)
- [ ] nRF52-based boards: UF2 bootloader detection and drag-drop flash
- [ ] ESP32-based boards: esptool flash with correct partition scheme
- [ ] Post-flash channel/region configuration over BLE or serial

### 6.5 3D Printer Boards (Klipper / Marlin)

Presets added: BTT SKR Mini E3 V3, BTT Octopus V1.1, BTT Manta M8P,
Creality 4.2.7.

- [ ] Klipper firmware compilation from web UI (select MCU, features)
- [ ] Marlin firmware compilation with PlatformIO backend
- [ ] ST-Link / DFU / SD card flash methods per board
- [ ] Stepper driver auto-detection (TMC2209, TMC2226, A4988)
- [ ] printer.cfg generator for Klipper (bed size, kinematics, probe type)

### 6.6 Flight Controllers (Betaflight / iNav)

Presets added: SpeedyBee F405 V4, Matek H743-SLIM.

- [ ] Betaflight / iNav / ArduPilot firmware as flash targets
- [ ] DFU mode detection and flashing
- [ ] Target board auto-detection from USB descriptor
- [ ] Pre-flash CLI diff export (save current config before update)

### 6.7 SDR Dongles

Presets added: RTL-SDR Blog V3/V4, HackRF One.

- [ ] HackRF firmware update via hackrf_spiflash
- [ ] RTL-SDR driver setup assistant (blacklist dvb_usb_rtl28xxu, install
  rtl-sdr udev rules)
- [ ] Bias-T configuration for RTL-SDR V3/V4

### 6.8 Routers & Networking (done)

- [x] TFTP failsafe flash (`POST /api/router/flash/tftp`) with dnsmasq
- [x] SSH sysupgrade for OpenWrt (`POST /api/router/flash/sysupgrade`)
- [x] Web admin upload (`POST /api/router/flash/web`)
- [ ] DD-WRT and FreshTomato as alternatives (future)

### 6.9 Single-Board Computers

Presets added: Pine64 (ROCK64, ROCKPro64, Quartz64, PineBook Pro),
Orange Pi (5, 5 Plus, Zero 3), Radxa (ROCK 5B, 5A), ODROID (N2+, M1, C4),
NVIDIA Jetson (Nano, Orin Nano), RISC-V (VisionFive 2, Milk-V Mars,
LicheeRV Dock).

- [ ] Armbian / DietPi / Ubuntu as flash targets for ARM SBCs
- [ ] eMMC vs. SD card vs. NVMe boot selection per board
- [ ] NVIDIA Jetson: JetPack / sdkmanager integration
- [ ] RISC-V boards: Debian/Ubuntu RISC-V image flashing
- [ ] U-Boot / Tow-Boot bootloader management

### 6.10 Electric Bikes

Presets added: Bafang M620 Ultra, TSDZ8, CYC X1 Pro/Stealth.
Info-only entries added for locked systems: Bosch CX/SX, Shimano EP8/EP801,
Yamaha PW-S2, Brose S Mag.

- [ ] Controller identification (Bafang BBSHD/BBS02, TSDZ2, Kunteng/KT, VESC)
- [ ] ST-Link flashing for STM8-based controllers (reuse existing ST-Link infra)
- [ ] bbs-fw integration (open-source Bafang BBSHD/BBS02 firmware)
- [ ] TSDZ2 OSF integration (open-source Tongsheng firmware)
- [ ] Stancecoke firmware support for KT sine wave controllers
- [ ] Parameter configuration UI:
  - Speed limits per assist mode (eco / touring / sport / turbo)
  - Motor and battery current limits
  - PAS levels and torque sensor curves
  - Throttle mapping and response
  - KERS / regenerative braking intensity
  - Street mode / offroad mode toggle
- [ ] Firmware backup before flash (read current controller image)
- [ ] Pre-flash safety checks (battery level, controller chip detection)
- [ ] Display firmware flashing (850C, 860C for TSDZ2)
- [ ] Recovery guide for bricked controllers
- [ ] "Not supported" info pages for locked systems (Bosch, Shimano, Yamaha,
  Brose) — explain why, link to third-party tuning dongles where applicable

### 6.11 Scooter Expansion

Presets added: Pure (Air Pro, Air Go, Advance), NIU (KQi2 Pro, KQi3 Pro,
KQi3 Max), Navee (N65, S65), Vsett (9+, 10+, 11+), Dualtron (Thunder 2,
Storm, Mini).

- [ ] BLE protocol reverse engineering for Pure, NIU, Navee
- [ ] UART protocol support for Vsett/Dualtron (Minimotors controller)
- [ ] Sine wave controller identification for performance scooters
- [ ] Community-contributed protocol decoders (plugin architecture, Phase 7)

### 6.12 Game Consoles (done)

- [x] Nintendo Switch: RCM detection + payload injection (`web/routes/console.py`)
- [x] Steam Deck: SteamOS recovery image writer
- [x] PS Vita: HENkaku/Enso CFW step-by-step guide
- [ ] Retro handhelds: GarlicOS, Onion OS, muOS (future)

### 6.13 Wearables

- [ ] PineTime: InfiniTime / Wasp-OS flash via BLE OTA or SWD
- [ ] Gadgetbridge integration for companion app pairing

### 6.14 Vehicles (research)

- [ ] CAN bus read/write tooling (prerequisite)
- [ ] OBD2 diagnostics (leverage OVMS patterns)
- [ ] NMEA 2000 / SignalK for marine
- [ ] ECU tuning (long-term research)

---

## Phase 7 — Platform Maturity (done)

*"The right amount of complexity is the minimum needed."*

### 7.1 Configuration System

- [x] YAML config support — loaders check `.yaml` first, fall back to `.cfg`
- [x] Migration endpoint (`POST /api/devices/migrate-yaml`)
- [x] Export/import/share device profiles via IPFS manifests
- [ ] Per-device-instance configuration (future)

### 7.2 Plugin Architecture

- [x] `DeviceDriver` protocol (detect, flash, backup, info) in `web/plugin.py`
- [x] `MonitorableDriver` and `UpdatableDriver` optional protocols
- [x] Auto-discovery from `web/plugins/` directory
- [x] Plugin registry with `GET /api/plugins`, detect, and info endpoints

### 7.3 Mobile App

- [x] PWA manifest + service worker (`web/static/manifest.json`, `web/static/sw.js`)
- [x] Offline support for static assets, network-first for HTML
- [ ] Web Bluetooth integration (future)
- [ ] Push notifications (future)

### 7.4 Integrations

- [ ] MQTT broker support (future)
- [ ] Home Assistant discovery (future)
- [ ] Multi-language documentation (future)

---

## Phase 8 — Build Your OS (done)

*"Don't just flash an OS — build one from scratch."*

### 8.1 Base Image Selection

- [x] Five distro backends: Ubuntu, Debian, Arch, Alpine, Fedora, NixOS
- [x] Target architecture picker (amd64, arm64, armhf, x86_64, aarch64)
- [x] Target device picker (generic PC, ARM64, RPi 3/4/5, VM)

### 8.2 Build Caching via IPFS

- [x] Base rootfs layer caching (skip debootstrap/pacstrap on cache hit)
- [x] Package layer caching (skip apt-get install on cache hit)
- [x] Package download cache (bind-mounted apt archives)
- [x] Layer CIDs recorded in build profiles for reproducibility
- [x] Layer sharing between users via IPFS manifests

### 8.3 Base Distro Customization

- [x] Ubuntu/Debian preseed generator (locale, partitioning, users, packages)
- [x] Arch Linux pacstrap profile
- [x] Alpine Linux answer file generator
- [x] Fedora Kickstart generator
- [x] NixOS configuration.nix generator

### 8.4 Build & Output

- [x] Build engine: debootstrap, pacstrap, apk, dnf, nix-build in chroot
- [x] Output formats: .img (raw disk), .iso (bootable), .tar.gz (rootfs)
- [x] Build log streaming to web UI in real time
- [x] Publish to IPFS after build

### 8.5 Profiles & Sharing

- [x] Save/load OS build profiles (JSON)
- [x] Community build gallery (`GET /api/os-builder/gallery`)
- [x] Gallery publish/import with Ed25519 signature verification
- [x] Fork gallery builds into editable profiles
- [x] Reproducibility check (`POST /api/os-builder/reproducibility`)

---

## Phase 6 — Priority Order

Not all device families are equal. This is the recommended sequence based on
community demand, existing infrastructure reuse, and effort-to-impact ratio.

| Priority | Family | Why now |
|----------|--------|---------|
| P0 | 6.1 fastboot phones | Largest demand. Pixel/OnePlus/Xiaomi dominate custom ROM installs. |
| P0 | 6.10 E-bikes (expand) | ST-Link infra already exists from scooter work. Config files ready. |
| P0 | 6.11 Scooter expansion | BLE infra exists. New brands need protocol RE. |
| P1 | 6.3 ESP32 / IoT | esptool is simple. Web Serial unlocks browser-only flashing. |
| P1 | 6.4 LoRa / Meshtastic | Same tooling as ESP32 + nRF52. Meshtastic community is growing fast. |
| P1 | 6.9 SBCs | SD card imaging already works. Armbian/DietPi are straightforward. |
| P1 | 6.2 Linux phones | Small but passionate community. PinePhone uses existing SD/fastboot paths. |
| P2 | 6.5 3D printer boards | Klipper compilation is complex. DFU/ST-Link flash is simpler first step. |
| P2 | 6.6 Flight controllers | Niche but straightforward DFU flashing. |
| P2 | 6.7 SDR dongles | Minimal flash workflow — mostly driver setup. |
| P2 | 6.8 Routers | OpenWrt support is high-value but requires per-device flash methods. |
| P3 | 6.12 Game consoles | Legal complexity (DMCA). Community interest but risky. |
| P3 | 6.13 Wearables | PineTime only viable target. Small audience. |
| P3 | 6.14 Vehicles | Research phase. CAN bus tooling is prerequisite. |

---

## Phase Summary

| Phase | Theme | Status | Key Deliverable |
|-------|-------|--------|-----------------|
| 0 | Foundations | Done | Flash tool, wizard, ROM discovery, IPFS, backup |
| 1 | Safety Net | Done | Recovery guides, firmware registry, pre-flash verification |
| 2 | CFW Builder | Done | Scooter CFW builder, phone debloat/privacy, e-bike flash |
| 3 | Live Dashboard | Done | Scooter BLE telemetry, register read/write, quick actions |
| 4 | OTA Updates | Done | Scooter OTA, phone one-click update, companion script |
| 5 | Community | Done | Device search, submissions, IPFS manifests, config channels |
| 6 | New Devices | Partial | Fastboot, routers, game consoles done; ESP/LoRa/3D printers in progress |
| 7 | Platform | Done | YAML config, plugin architecture, PWA |
| 8 | Build Your OS | Done | 5 distros, IPFS layer caching, community gallery |

---

## Guiding Principles

Taken from the [Manifesto](MANIFESTO.md) and applied to roadmap decisions:

1. **Safety first** — Phase 1 before Phase 2. Recovery before customization.
2. **Complexity is our problem** — Every new feature must have a guided path.
   If a user needs to read a forum to figure it out, we failed.
3. **Teach, don't hide** — The CFW builder shows diffs. The dashboard explains
   error codes. The wiki documents protocols. Dry-run mode stays forever.
4. **Open source or go home** — No proprietary dependencies. No cloud lock-in.
   IPFS over CDN. Community wiki over walled garden.
5. **Ship incrementally** — Each phase delivers standalone value. Users don't
   wait for the "full platform" to benefit.
