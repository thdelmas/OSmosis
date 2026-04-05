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

## Phase 1 — Safety Net (partial)

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
- [x] Battery level check (>25% via ADB) integrated into pre-flight
- [x] Structured error guides (`useErrorGuide.js`): stale sessions, signature verification, low battery, locked bootloaders, and more

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
- [x] Install Apps page (`PageApps.vue`): catalog (F-Droid, Termux, K-9 Mail, Signal), URL, or local APK via `POST /api/apps/install`

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

### 6.15 Desktop & Laptop Firmware

- [ ] Coreboot/Libreboot flash via `flashrom` for ThinkPads (X200/T400/X230/T430)
- [ ] MrChromebox Chromebook full ROM replacement integration
- [ ] Framework Laptop EC firmware flash via `flash_ec`
- [ ] System76 firmware update via `system76-firmware-cli` / FWUPD
- [ ] Protectli Vault / PC Engines APU Coreboot flash via `flashrom`
- [ ] Intel ME neutralization guidance (`me_cleaner`)

### 6.16 Digital Cameras

- [ ] Canon DSLR Magic Lantern install guide (SD card, non-destructive)
- [ ] Canon point-and-shoot CHDK autoboot setup
- [ ] Sony OpenMemories-Tweak via pmca-console
- [ ] Nikon-Patch firmware patching (EXPEED 2/3 models)
- [ ] GoPro Labs firmware install guide
- [ ] DJI firmware management via dji-firmware-tools (with legal disclaimers)

### 6.17 E-Readers

- [ ] Kobo KOReader + NickelMenu install (USB mass storage, no exploit)
- [ ] reMarkable Toltec package manager bootstrap via SSH
- [ ] PocketBook KOReader sideload via SDK
- [ ] Kindle jailbreak guide (WinterBreak) + KOReader install
- [ ] Onyx Boox APK sideloading and Magisk root guide

### 6.18 Smart TVs & Streaming Devices

- [ ] LG webOS Homebrew Channel install (rootmy.tv exploit flow)
- [ ] Android TV / Google TV Magisk root + custom launcher
- [ ] Amazon Fire TV debloat and custom launcher via ADB
- [ ] Samsung SamyGO integration research

### 6.19 Robot Vacuums

- [ ] Roborock Valetudo install via DustBuilder firmware
- [ ] Dreame Valetudo install (UART rooting)
- [ ] Xiaomi Mi Robot Valetudo install
- [ ] Safety checks: model/serial verification before rooting

### 6.20 Lab & Test Equipment

- [ ] Rigol DS1054Z bandwidth unlock via SCPI
- [ ] Siglent option unlock via SCPI license keys
- [ ] sigrok `fx2lafw` flash for Cypress FX2 logic analyzers
- [ ] SCPI instrument discovery and command interface

### 6.21 Keyboards & Input Devices

- [ ] QMK firmware build and flash via QMK Toolbox / `dfu-util`
- [ ] ZMK firmware build and UF2 drag-and-drop flash
- [ ] VIA/VIAL live keymap configuration (no flash)
- [ ] Keyboard MCU auto-detection (STM32, ATmega, nRF52, RP2040)

### 6.22 Synthesizers & Audio

- [ ] Mutable Instruments audio bootloader flash (WAV file method)
- [ ] Korg logue SDK custom oscillator/effect upload via Sound Librarian
- [ ] MOD Dwarf LV2 plugin install via web UI

### 6.23 Solar & Energy Devices

- [ ] OpenDTU / AhoyDTU ESP32 gateway flash (esptool)
- [ ] Victron Venus OS install on Raspberry Pi
- [ ] BMS parameter configuration via BLE (JBD/Daly/JK)
- [ ] OpenEVSE firmware update (ESP32 + ATmega)

### 6.24 Calculators

- [ ] TI-84 Plus CE arTIfiCE jailbreak + Cesium install guide
- [ ] TI-Nspire Ndless installer
- [ ] NumWorks Omega/Upsilon flash via WebDFU
- [ ] OS version compatibility checks (critical for TI and NumWorks)

### 6.25 Retro Handhelds

- [ ] Anbernic RG35XX family CFW flash (GarlicOS, muOS, KNULLI)
- [ ] Miyoo Mini Onion OS / MiniUI install (FAT32 SD card)
- [ ] MiSTer FPGA core management (Update_All)
- [ ] TrimUI / Powkiddy KNULLI / ROCKNIX flash
- [ ] SD card image writing (reuse existing bootable SD infra)

### 6.26 Server BMC/IPMI

- [ ] OpenBMC flash guide for supported platforms (Meta, IBM POWER)
- [ ] Supermicro IPMI firmware update via web UI / SUM CLI
- [ ] BMC auto-detection (AST2500/AST2600)

### 6.27 Other Emerging Categories

- [ ] Agricultural: AgOpenGPS ESP32 auto-steer flash
- [ ] Wheelchair: SuperHouse WMC/PWC open controller flash
- [ ] Satellite: SatNOGS ground station RPi image
- [ ] Storage: NVMe firmware update via `nvme-cli`
- [ ] Medical data access: OSCAR/xDrip+ setup guides (no device flashing)

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

## Phase 9 — LETHE: Agent OS for Abandoned Hardware

*"The app store era is over. The agent is the interface."*

LETHE is a companion project — an agent-first Linux OS that gives abandoned
devices a second life. Instead of apps, the interface is a conversational AI
agent with full system access. Voice-first, text-second.

Repository: [github.com/thdelmas/bender](https://github.com/thdelmas/bender)

### 9.1 Voice-First Agent Interface (done)

- [x] Web-based chat UI (mic button, waveform, streaming responses)
- [x] Whisper STT integration (server-side speech-to-text)
- [x] espeak TTS integration (server-side text-to-speech)
- [x] Claude API streaming agent runtime
- [x] Encrypted API key storage on device

### 9.2 Device Setup

- [x] API key paste input
- [x] QR code scanner (camera-based, client-side decoding)
- [x] QR code generator page (key never leaves the browser)
- [ ] Free-tier bootstrap (limited agent for setup-only)

### 9.3 Agent Capabilities

- [ ] Shell access (agent can run commands on the device)
- [ ] Package management (agent can install/remove software)
- [ ] File management (agent can read/write/search files)
- [ ] Network configuration (WiFi, Bluetooth)
- [ ] System monitoring (battery, storage, memory)

### 9.4 Device Image

- [ ] Minimal Linux image for NovaThor U8500 (Samsung Galaxy Ace 2)
- [ ] Boot into browser + agent interface directly
- [ ] postmarketOS base with MCDE display driver fix
- [ ] Image builder for other target devices (RPi, PinePhone, etc.)

### 9.5 Multi-Provider Support

- [ ] OpenAI API support (GPT-4o)
- [ ] Local LLM support (llama.cpp / Ollama for capable devices)
- [ ] Provider selection in settings
- [ ] Automatic fallback (cloud → local → offline commands)

---

## Phase 9b — LETHE Protection Modules

*"The guardian protects more than the device."*

LETHE extends beyond OS/device management into personal protection
domains. Each module is opt-in, local-first, and degrades gracefully
across device tiers. See `lethe/docs/design/protection-domains.md` for
the full investigation.

### 9b.1 Bios — Protect Your Health

- [ ] Emergency medical card on lockscreen (no unlock required)
- [ ] EXIF/metadata stripping on health-related media
- [ ] OSCAR (CPAP) and xDrip+ (CGM) data access — no cloud required
- [ ] Gadgetbridge wearable vitals integration
- [ ] Default-deny sensor permissions for health apps

### 9b.2 PreuJust — Protect Your Money

- [ ] Phishing URL detection in SMS/notifications (heuristic, local)
- [ ] Financial app permission audit (contacts/SMS/accessibility flags)
- [ ] Scam call screening (local community-sourced spam DB)
- [ ] Payment screen guardian — vision model flags deceptive dialogs
  (deeproot only)
- [ ] Subscription surface from bank notifications (local NLP)

### 9b.3 Vigil — Protect Your Privacy

- [ ] Breach monitoring via local bloom filter (HIBP-style, no raw
  credential sent)
- [ ] Tracker report — daily/weekly blocked tracker & DNS summary
- [ ] Permission drift alert on app updates
- [ ] Password reuse detection via KeePassXC vault export
- [ ] Account cleanup suggestions (opt-in, from browser history)

### 9b.4 Mnemo — Protect Your Legacy

- [ ] Legacy contacts: designated recipients on DMS trigger
- [ ] Account inventory with per-account instructions (encrypted,
  /persist)
- [ ] Posthumous message vault (encrypted, released on DMS)
- [ ] Wipe-on-trigger option alongside or instead of data release
- [ ] Posthumous node integration (federated dead man's switch)

### 9b.5 Hora — Protect Your Time

- [ ] Notification triage: classify by urgency, batch low-priority
- [ ] Focus mode: one-tap silence, only emergency + LETHE alerts
- [ ] App usage transparency: network/camera/mic/GPS usage last 24h
- [ ] Screen time awareness: opt-in report, no gamification
- [ ] Dark pattern detection via vision model (deeproot only)

### 9b.6 Egida — Protect Your Safety (research)

- [ ] Emergency SOS via hardware button combo
- [ ] Time-limited encrypted location sharing (Briar/Signal/SimpleX)
- [ ] Travel mode: geofence triggers (VPN, disable biometrics, burner)
- [ ] Duress unlock: secondary code opens decoy + silent DMS trigger

### 9b.7 Themis — Know Your Rights (research)

- [ ] Offline jurisdiction-aware rights cards (police, border, protest)
- [ ] Document scanner with local OCR (deeproot) or manual entry
- [ ] Quick-dial legal contacts list
- [ ] Warrant canary integration (SECURITY-ROADMAP P3)

### 9b.8 Oikos — Protect Your Home (research)

- [ ] IoT device audit via LAN scan (manufacturer, firmware version)
- [ ] Gladys bridge for smart home anomaly alerts
- [ ] Network intrusion detection (ARP + eBPF, SECURITY-ROADMAP P2)
- [ ] Matter protocol bridge for direct device control

### 9b Priority Order

| Priority | Module | Why |
|----------|--------|-----|
| **P0** | Vigil (Privacy) | Most primitives exist (Tor, firewall, hosts). Packaging + UX. |
| **P0** | Mnemo (Legacy) | DMS already built. Legacy contacts are an extension. |
| **P1** | Bios (Health) | Sensor permissions exist. Medical card is low-effort, high-value. |
| **P1** | PreuJust (Money) | Phishing + permission audit reuse existing infra. |
| **P1** | Hora (Time) | Notification filtering is OS-level. No new dependencies. |
| **P2** | Egida (Safety) | Needs location services + hardware button interception. |
| **P2** | Oikos (Home) | Depends on Gladys integration (competitive-gaps #3b). |
| **P3** | Themis (Rights) | Requires per-jurisdiction curation. High effort. |

---

## Phase 10 — Usability & Accessibility

*"If a twelve-year-old can't figure it out, we failed."*

Manifesto sections 4 and 5 set a high bar: every screen should answer "What
is happening? What do I do next? Is it safe?" without the user asking, and
the interface must work for everyone regardless of technical background, age,
ability, or language. This phase closes the gap between that promise and the
current UI.

### 10.0 Critical Safety Fixes

These prevent data loss or bricked devices. Ship before anything else.

- [ ] **Multi-device selection UI** — when multiple USB devices are detected,
  show a picker instead of silently choosing one. Display device name, serial,
  and connection type so users can distinguish between devices.
- [ ] **Show physical button combos in StepInstall** — `downloadModeCombo` and
  `recoveryModeCombo` are already computed but never rendered. Display them
  with illustrations or diagrams so users can enter recovery/download mode
  without Googling.
- [ ] **Remove or gate "Skip" in StepConnect** — the current "Skip to next
  step" button lets users proceed without a device, creating a guaranteed
  failure at flash time. Either remove it or require explicit acknowledgement
  ("I understand flashing will fail without a connected device").
- [ ] **Confirmation on wizard state restore** — when localStorage has saved
  wizard state from a previous session, prompt the user ("Continue where you
  left off with [Device X]?" / "Start fresh") instead of silently restoring.
  Prevents flashing the wrong ROM after plugging in a different device.

### 10.1 Error Handling & Recovery

- [ ] **Global `.info-box--error` styling** — add a distinct red/error variant
  to the global stylesheet so errors are visually distinguishable from
  warnings across all wizard steps, not just StepInstall.
- [ ] **Actionable error messages** — parse backend error types
  (`stale_session`, `usb_no_adb`, `permission_denied`) into human-readable
  guidance with concrete next steps. Replace generic messages like "Download
  failed. Check terminal output" with specific recovery instructions.
- [ ] **Automatic retry for transient failures** — add configurable retry with
  exponential backoff for network operations (ROM downloads, IPFS fetches).
  Show retry count and "Give up" button so users aren't stuck.
- [ ] **"Try again" buttons on failure** — every error state should offer a
  retry action instead of requiring manual navigation back through the wizard.
- [ ] **Samsung Download Mode guidance** — when a device is detected in
  Download Mode, explain clearly that this is a stuck state (not
  "downloading"), show Samsung-specific recovery steps, and surface the
  button combo to exit.

### 10.2 Progress & Feedback

- [ ] **Download progress bar** — implement a reliable progress indicator for
  ROM downloads and file transfers. Parse tool output for percentage, speed,
  and ETA. When percentage isn't available, show an indeterminate progress bar
  with elapsed time — never show nothing.
- [ ] **Device detection loading state** — when `autoDetect()` runs on mount,
  show "Scanning for connected devices..." instead of a bare spinner.
- [ ] **Task status guidance** — when TaskBar shows a "lost" task, explain what
  happened and offer "Restart task" or "Start over" actions instead of just
  an hourglass emoji.
- [ ] **Stage-level progress in wizard** — show completed / in-progress /
  remaining stages within each step (e.g., "Downloading ROM → Verifying
  checksum → Flashing" with visual indicators for each).

### 10.3 Accessibility (WCAG AA Baseline)

- [ ] **`aria-live` regions for status updates** — add `aria-live="polite"` to
  TerminalOutput status line, TaskBar status, and download progress so screen
  readers announce state changes.
- [ ] **Keyboard navigation for card selections** — add `tabindex="0"`,
  `role="option"`, and `@keydown.enter` / `@keydown.space` handlers to
  category selection cards (StepIdentify) and ROM selection cards
  (StepSoftware).
- [ ] **Fix disabled button contrast** — replace `opacity: 0.5` on
  `.btn-primary:disabled` with explicit low-contrast colors that still meet
  WCAG AA 4.5:1 ratio.
- [ ] **Accessible loading buttons** — `.btn-loading` currently hides text
  with `color: transparent`. Add `aria-label="Loading"` and
  `aria-busy="true"` so assistive tech can report the state.
- [ ] **Hold-to-confirm accessibility** — add `aria-label` describing the
  hold-to-confirm interaction on StepLoad, and provide a keyboard-accessible
  alternative (e.g., press-and-hold Enter, or a two-step confirm fallback).
- [ ] **Terminal output contrast** — verify `.terminal-status--error` red on
  dark background meets 4.5:1 contrast. Adjust color values if needed.

### 10.4 Contextual Help & Guidance

- [ ] **Explain recovery selection** — StepSoftware's recovery picker
  (required recovery vs. preset vs. TWRP) should explain in plain language
  why the choice matters and what each option means, not just list names.
- [ ] **Pre-flight guidance in StepConnect** — before the user plugs in,
  proactively show "Trust this computer?" and USB debugging instructions
  instead of only surfacing them in error messages after failure.
- [ ] **Smart terminal error suggestions** — parse common error patterns in
  terminal output ("permission denied" → suggest running with elevated
  privileges; "device not found" → check USB cable) and surface them as
  inline tips above the raw log.
- [ ] **Glossary keyboard access** — GlossaryTip should be openable with
  Enter/Space when focused, and remain open on mobile until explicitly
  dismissed.

### 10.5 Mobile & Responsive

- [ ] **Terminal touch scrolling** — prevent TerminalOutput from capturing
  touch scroll events that block page scrolling. Add horizontal scroll for
  wide output lines.
- [ ] **Header controls on small screens** — ensure language, font-size, and
  theme buttons in AppHeader don't stack awkwardly below 480px. Consider a
  collapsed menu or icon-only mode.
- [ ] **Tap target sizing** — audit all interactive elements for minimum 44x44
  CSS pixel touch targets per WCAG 2.5.5.

### 10.6 Search & Device Identification

- [ ] **Relevance-ranked search results** — when StepIdentify returns many
  matches, sort by similarity score and visually highlight the best match.
- [ ] **Explain disabled "Proceed" button** — when `canProceed` is false, show
  a message explaining what's missing ("Select a brand to continue") instead
  of just graying out the button.
- [ ] **ROM path validation** — validate manual ROM paths in real time (check
  file exists, correct extension) instead of failing silently at flash time.

---

## Phase 10 — Production Deployment & Security Hardening

*"If you ship it, harden it."*

Inspired by server-hardening and provisioning patterns. OSmosis should be
safe to self-host on a Raspberry Pi, a home server, or any always-on
appliance — not just run locally for a quick flash.

### 10.1 Reverse Proxy & TLS

- [ ] `scripts/setup-nginx.sh` — auto-generate self-signed certs and configure
  nginx as a reverse proxy in front of Flask
- [ ] Let's Encrypt integration for public-facing instances (`certbot` automation)
- [ ] `make deploy` target that runs the full hardening stack in one shot

### 10.2 Firewall & Intrusion Prevention

- [ ] `scripts/setup-firewall.sh` — idempotent iptables/nftables script that
  opens only the ports OSmosis needs (443/5000 + USB passthrough)
- [ ] fail2ban jail for the web UI (rate-limit failed requests, block scanners)
- [ ] portsentry integration for network-exposed instances (optional)

### 10.3 Firmware Integrity Monitoring

- [ ] Scheduled checksum verification of cached firmware images (detect
  tampering between download and flash)
- [ ] Alert in the web UI when a cached image no longer matches its expected
  hash
- [ ] Config file integrity monitoring (hash-based, cron-triggered)

### 10.4 Privilege Isolation

- [ ] Run Flask as an unprivileged user; escalate only for flash operations
  (write to block devices, USB access)
- [ ] Clearly flag elevated operations in the UI ("this step requires root")
- [ ] Audit log of all privilege-escalated operations

### 10.5 Remote Access Hardening

- [ ] SSH tunnel documentation for remote OSmosis instances (avoid exposing
  HTTP directly)
- [ ] Optional token-based authentication for the web UI (generated on first
  run, no default credentials — ever)
- [ ] Rate limiting on all API endpoints

---

## Phase 11 — Post-Flash Automation & Device Orchestration

*"The flash is step one. Configuration is step two."*

Inspired by Ansible-based provisioning patterns. After flashing, many devices
need setup — Wi-Fi, locale, packages, hardening. OSmosis should handle that
too.

### 11.1 Resumable & Idempotent Flash Workflows

- [ ] Break flash workflows into discrete stages: `download → verify → flash →
  post-configure`
- [ ] Resume from the last failed stage instead of restarting the entire process
- [ ] Skip download if firmware is cached and checksum matches
- [ ] Skip flash if device already reports the target firmware version
- [ ] Stage status tracking in the UI (completed / in-progress / failed / skipped)

### 11.2 Declarative Device Profiles

- [ ] Structured YAML profile per device: firmware URL, checksum, flash tool,
  partition layout, required privileges, post-flash steps
- [ ] Backend consumes profiles generically — adding a device means adding a
  file, not editing Python code
- [ ] Profile validation schema (JSON Schema or Pydantic model)
- [ ] Migration tool from current `.cfg` files to the new profile format

### 11.3 Post-Flash Configuration Engine

- [ ] Ansible playbook runner: generate a temporary inventory with the device's
  IP/connection, run a device-specific playbook after flash
- [ ] Built-in playbooks for common post-flash tasks:
  - Wi-Fi / network configuration
  - Locale, timezone, hostname
  - Package installation
  - SSH key deployment
  - Hardening presets (firewall, fail2ban, unattended-upgrades)
- [ ] Custom playbook upload and execution from the web UI
- [ ] Playbook gallery (community-contributed, signed, IPFS-distributed)

### 11.4 Dynamic Device Inventory

- [ ] Auto-detect USB/serial/BLE-connected devices and map them to device
  profiles (extend current ADB + USB VID detection)
- [ ] Network device discovery (mDNS/SSDP) for post-flash configuration of
  networked devices (routers, SBCs, IoT)
- [ ] Inventory view in the web UI showing all detected devices, their status,
  and available actions

### 11.5 Composed Workflows

- [ ] "Flash + Configure" — full setup in one flow
- [ ] "Configure only" — for devices already running the target OS
- [ ] "Verify only" — check firmware integrity without flashing
- [ ] User-defined workflow templates (chain stages in any order)

---

## Phase 6 — Priority Order

Not all device families are equal. This is the recommended sequence based on
community demand, existing infrastructure reuse, and effort-to-impact ratio.

| Priority | Family | Why now |
|----------|--------|---------|
| ~~P0~~ | ~~6.1 fastboot phones~~ | ~~Done~~ |
| P0 | 6.10 E-bikes (expand) | ST-Link infra already exists from scooter work. Config files ready. |
| P0 | 6.11 Scooter expansion | BLE infra exists. New brands need protocol RE. |
| P1 | 6.3 ESP32 / IoT | esptool is simple. Web Serial unlocks browser-only flashing. |
| P1 | 6.4 LoRa / Meshtastic | Same tooling as ESP32 + nRF52. Meshtastic community is growing fast. |
| P1 | 6.9 SBCs | SD card imaging already works. Armbian/DietPi are straightforward. |
| P1 | 6.2 Linux phones | Small but passionate community. PinePhone uses existing SD/fastboot paths. |
| P2 | 6.5 3D printer boards | Klipper compilation is complex. DFU/ST-Link flash is simpler first step. |
| P2 | 6.6 Flight controllers | Niche but straightforward DFU flashing. |
| P2 | 6.7 SDR dongles | Minimal flash workflow — mostly driver setup. |
| ~~P2~~ | ~~6.8 Routers~~ | ~~Done~~ |
| ~~P3~~ | ~~6.12 Game consoles~~ | ~~Done~~ |
| P3 | 6.13 Wearables | PineTime only viable target. Small audience. |
| P3 | 6.14 Vehicles | Research phase. CAN bus tooling is prerequisite. |
| P1 | 6.15 Desktop/laptop firmware | Coreboot/Libreboot community is large. flashrom is mature. ThinkPads are iconic. |
| P1 | 6.17 E-readers | Kobo/reMarkable need no exploit. Kindle jailbreak is well-documented. Large audience. |
| P1 | 6.21 Keyboards | QMK/ZMK ecosystem is huge. DFU/UF2 flash is simple. |
| P1 | 6.25 Retro handhelds | SD card flash reuses existing infra. KNULLI/Onion OS communities are booming. |
| P2 | 6.16 Digital cameras | Magic Lantern/CHDK are non-destructive (SD card). Large photography community. |
| P2 | 6.18 Smart TVs | webOS Homebrew Channel is accessible. Fire TV debloat is high-demand. |
| P2 | 6.19 Robot vacuums | Valetudo is mature but UART rooting is hardware-intensive. |
| P2 | 6.20 Lab equipment | SCPI unlock is simple. Niche but enthusiastic community. |
| P2 | 6.22 Synthesizers | Mutable Instruments audio bootloader is unique. Korg SDK is officially open. |
| P2 | 6.23 Solar & energy | OpenDTU reuses ESP32 tooling. Victron is officially open. |
| P2 | 6.24 Calculators | Student audience aligns with manifesto. WebDFU is browser-native. |
| P3 | 6.26 Server BMC | Enterprise niche. OpenBMC is complex. |
| P3 | 6.27 Other emerging | Agriculture, wheelchair, satellite — small audiences, research phase. |

---

## Phase Summary

| Phase | Theme | Status | Key Deliverable |
|-------|-------|--------|-----------------|
| 0 | Foundations | Done | Flash tool, wizard, ROM discovery, IPFS, backup |
| 1 | Safety Net | Partial | Recovery guides, firmware registry, pre-flash verification (1.0 housekeeping remaining) |
| 2 | CFW Builder | Done | Scooter CFW builder, phone debloat/privacy, e-bike flash |
| 3 | Live Dashboard | Done | Scooter BLE telemetry, register read/write, quick actions |
| 4 | OTA Updates | Done | Scooter OTA, phone one-click update, companion script |
| 5 | Community | Done | Device search, submissions, IPFS manifests, config channels |
| 6 | New Devices | Partial | Fastboot, routers, consoles done; 13 new categories added (cameras, e-readers, TVs, vacuums, keyboards, synths, handhelds, etc.) |
| 7 | Platform | Done | YAML config, plugin architecture, PWA |
| 8 | Build Your OS | Done | 5 distros, IPFS layer caching, community gallery |
| 9b | LETHE Protection Modules | Planned | Bios (health), PreuJust (money), Vigil (privacy), Mnemo (legacy), Hora (time), Egida (safety), Themis (rights), Oikos (home) |
| 9c | Usability & Accessibility | Planned | Multi-device picker, progress bars, error recovery, WCAG AA, mobile UX |
| 10 | Deployment & Security | Planned | Nginx + TLS, firewall, fail2ban, integrity monitoring, privilege isolation |
| 11 | Post-Flash Automation | Planned | Resumable workflows, declarative profiles, Ansible post-config, device inventory |

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
6. **Harden by default** — Security is baked in, not bolted on. No default
   credentials, no exposed dev servers, no skipped checksums. Every
   deployment should be production-grade out of the box.
7. **Idempotent everything** — Every operation should be safe to re-run.
   Resumable workflows, cached downloads, skip-if-done checks. Users
   should never have to start over because one step failed.
