# Osmosis Roadmap

From flashing tool to device freedom platform.

This roadmap is organized into phases. Each phase builds on the previous one
and delivers standalone value. Phases are not strictly sequential — work can
overlap where dependencies allow.

See [DESIGN.md](DESIGN.md) for the architectural picture each phase plugs
into, and [MANIFESTO.md](MANIFESTO.md) for the principles that rank the work.

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

- [x] Add USB VID/PID entries for new vendors to the detection registry
- [x] Add i18n strings for new device labels and categories
- [x] Handle `support_status: not-supported` in the UI for locked systems
- [x] Add device category grouping in the wizard for new families
- [x] Stub documentation pages in `docs/devices/`

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

- [x] Post-flash health check via ADB — `GET /api/diagnostics` (also aliased as
  `GET /api/device-info`)
- [x] Installed ROM version (`rom_name`), root/Magisk status (`has_root`,
  `has_magisk`), battery (`battery.{level, status, health, temperature,
  voltage}`), storage (`storage.{total, used, free}`), bootloader lock state,
  uptime — all in [`web/routes/diagnostics.py`](../../web/routes/diagnostics.py)

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

### 4.3 Phone Update Pipeline (future)

- [ ] Companion Termux script with ROM update checker — demoted from 4.2
  on 2026-05-09 (audit gap #18). LETHE already provides on-device Termux
  integration; an OSmosis-side duplicate didn't earn its weight. Revisit
  if non-LETHE users request it.

### 4.4 ESP/IoT OTA (future)

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

- [x] Kobo KOReader + NickelMenu install (USB mass storage, no exploit)
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

## Phase 10 — Usability & Accessibility (done)

*"If a twelve-year-old can't figure it out, we failed."*

Manifesto sections 4 and 5 set a high bar: every screen should answer "What
is happening? What do I do next? Is it safe?" without the user asking, and
the interface must work for everyone regardless of technical background, age,
ability, or language. This phase closes the gap between that promise and the
current UI.

### 10.0 Critical Safety Fixes

These prevent data loss or bricked devices. Ship before anything else.

- [x] **Multi-device selection UI** — `/api/detect` returns
  `{multiple: true, devices: [...]}` when several ADB devices are connected.
  StepConnect now renders a picker (device label, serial, ADB state) instead
  of silently dropping the response. Picking a device sets it via `setDevice`
  and proceeds normally.
- [x] **Show physical button combos in StepInstall** — `downloadModeCombo`
  and `recoveryModeCombo` are rendered at every prompt-for-mode site,
  including the manual-recovery-install fallback and sideload-failure error
  messages. StepFix's failure message also embeds the combo.
- [x] **Gate "Skip" in StepConnect** — the Skip button reveals a warning
  panel ("Flashing will fail without a connected device. Only skip if you
  want to explore the interface.") and only proceeds via an explicit
  "I understand, continue anyway" action.
- [x] **Confirmation on wizard state restore** — App.vue's `peek()` checks
  for saved state on mount and shows a banner ("Continue where you left off
  with [Device X]?" / "Start fresh") before restoring. Silent restore only
  happens when the current route already matches the saved one.

### 10.1 Error Handling & Recovery

- [x] **Global `.info-box--error` styling** — variant now sets a red
  border, a 4px red left-accent, a soft red background tint, and injects a
  red `!` badge via `::before` so error boxes are unambiguously distinct
  from `--warn` (orange, no badge). Cascading `color: var(--red)` removed —
  it had been turning body text and child buttons red across every wizard
  step that uses the variant. Red is now applied only to a leading
  `<strong>`/`<h3>`/`<h4>` if present.
- [x] **Actionable error messages** — the `__error_type:` taxonomy was
  already wired up for 7 flash-side conditions; the gap was the
  network-download side, which used to bottom out at the generic "Download
  failed." Added a `download_failed` guide in
  [`useErrorGuide.js`](../../frontend/src/composables/useErrorGuide.js)
  with concrete next-step instructions ("check internet, wait a few
  minutes, try a different mirror, watch out for captive portals") and
  emit it at the four retry-exhausted sites:
  [`romfinder_download.py`](../../web/routes/romfinder_download.py),
  [`workflow_engine.py`](../../web/workflow_engine.py),
  [`workflow_update.py`](../../web/routes/workflow_update.py), and
  [`ipfs.py`](../../web/routes/ipfs.py). TerminalOutput now renders the
  typed guide AND the regex-matched hints together (was `v-else-if`) so a
  generic guide still lets a specific stderr-derived cause like "Disk
  full" or "Connection refused" surface alongside it.
- [x] **Automatic retry for transient failures** — `Task.run_shell_with_retry`
  in [`web/core.py`](../../web/core.py) wraps a `run_shell` call in up to N
  attempts with exponential backoff (5s → 10s → 20s for the default 3
  attempts), emits structured `__retry:{n}/{max}` markers plus
  human-readable lines, and aborts the wait immediately when the task is
  cancelled. The four highest-leverage download sites are wrapped:
  `wget` and `ipfs get` in [`romfinder_download.py`](../../web/routes/romfinder_download.py),
  the workflow `wget` in [`workflow_engine.py`](../../web/workflow_engine.py),
  the workflow-update `wget`/`ipfs get` pair in
  [`workflow_update.py`](../../web/routes/workflow_update.py), and the
  generic IPFS fetch in [`ipfs.py`](../../web/routes/ipfs.py). All `wget`
  invocations gained `-c` so retries resume rather than restart from byte 0.
  Frontend renders a `terminal-retry` banner via `parseRetryStatus` in
  [`TerminalOutput.vue`](../../frontend/src/components/shared/TerminalOutput.vue)
  with attempt-count and an always-visible "Give up" button (with confirm),
  so the abort path no longer requires expanding the technical-details
  section first.
- [x] **"Try again" buttons on failure** — audit done across every site
  using `info-box--error`; explicit retry buttons added to PageFlashRecovery,
  PageFlashStock, and PageApps (the three pages whose error boxes previously
  relied on the user noticing the still-enabled main action button at the
  top). All wizard steps already had explicit retry/Try-again actions.
- [x] **Samsung Download Mode guidance** — StepConnect's Download Mode
  panel now leads with "This is a stuck state, not an active download" and
  names Samsung explicitly so users understand the misconception. The
  manual exit sequence (unplug → hold Power 10s → optional battery pull →
  press Power without USB → replug) is already surfaced under "If
  automatic reboot doesn't work", and the auto-reboot button stays the
  primary action.

### 10.2 Progress & Feedback

- [x] **Download progress bar** — TerminalOutput renders a determinate bar
  when tool output contains `<n>%`, an indeterminate bar otherwise, and an
  always-visible elapsed-time counter. Now also parses transfer speed
  (`1.23 MB/s`, `456K/s`) and ETA (`eta 5s`, `eta 1m 30s`) from common
  tool output (wget, curl, ipfs) and renders them under the bar.
- [x] **Device detection loading state** — StepConnect shows "Scanning for
  connected devices..." (or the microcontroller equivalent) immediately on
  detect, with an `aria-live="polite"` region and a tabular elapsed-time
  counter that appears after 3s.
- [x] **Task status guidance** — TaskBar's lost-task path now shows a
  headline ("Task no longer tracked"), an explanation of likely causes
  (server restart vs. completion-while-away), guidance to verify on the
  device, and explicit "Start over" / "Dismiss" actions. Start over
  dismisses the task and navigates to the wizard root.
- [x] **Stage-level progress in wizard** — TerminalOutput now parses the
  `[N/M] Label` lines emitted by `Task.progress()` and renders a compact
  stepper: a row of dots (filled green for done, pulsing accent for current,
  hollow for upcoming) plus a "Step N of M — Label" caption. Surfaces stage
  data the backend was already emitting in
  [`romfinder_download.py`](../../web/routes/romfinder_download.py),
  [`workflow_engine.py`](../../web/workflow_engine.py),
  [`lethe_ota.py`](../../web/routes/lethe_ota.py),
  [`self_update.py`](../../web/routes/self_update.py), and others — these
  used to be visible only by expanding the technical-details terminal log.

### 10.3 Accessibility (WCAG AA Baseline)

- [x] **`aria-live` regions for status updates** — TerminalOutput status line
  uses `aria-live="polite"`; error guides/hints use `role="alert"`; the
  progress bar uses `role="progressbar"` with `aria-valuenow/min/max`.
  TaskBar header now uses `aria-live="polite"` and per-task containers
  flip `aria-busy="true"` while running.
- [x] **Keyboard navigation for card selections** — StepGoal and
  StepCategory cards have `tabindex="0"` + Enter/Space handlers. Card grids
  in StepSoftware (ROMs) and StepIdentify (recent / multi-detect / device
  search) are already `<button>` elements, which give keyboard semantics
  for free.
- [x] **Visibly disabled buttons** — `.btn-*:disabled` combines `opacity`
  with `filter: saturate(0.3)` so the disabled state is unambiguous across
  all four themes, not just dim.
- [x] **Accessible loading buttons** — `.btn-loading` no longer hides the
  label (`color: transparent` removed); the spinner sits to the right and
  the label stays visible. `[aria-busy="true"]` on a `.btn` is now an
  equivalent selector, so call sites can use the proper a11y attribute
  instead of (or alongside) the class without losing styling.
- [x] **Hold-to-confirm accessibility** — StepLoad's hold-to-confirm button
  has a holding-state-aware `aria-label` ("Press and hold Enter or Space for
  1.5 seconds to confirm flash" / "Keep holding to confirm flash operation"),
  and supports both Enter and Space (the canonical button-activation key) as
  keyboard equivalents. `startHold` now guards against re-entry so keyboard
  autorepeat cannot leak timers or fire `executeConfirmed` multiple times,
  and `@blur` cancels an in-progress hold if focus leaves the button. The
  data-loss-acknowledgement checkbox upstream of the button already provides
  the two-step gate.
- [x] **Terminal output contrast** — verified all four themes meet WCAG
  AA 4.5:1 for the actual red text (`.terminal-error-guide-title`, `.terminal
  .line.error`): dark 4.72:1 / 5.25:1, light 4.99:1 / 5.49:1, hi-contrast dark
  ≫ 5:1, hi-contrast light 5.72:1 / 5.51:1. `.terminal-status--error` itself
  is border-only (WCAG 1.4.11 → 3:1, comfortably exceeded). No color changes
  required.

### 10.4 Contextual Help & Guidance

- [x] **Explain recovery selection** — StepSoftware's `recovery-pick` phase
  now leads with the question being asked ("How should we install X?"),
  explains *why* a custom recovery is needed (factory recovery only accepts
  manufacturer-signed updates), and each option spells out the consequence
  of picking it (including the specific "signature verification failed"
  error users will hit if they skip).
- [x] **Pre-flight guidance in StepConnect** — added a "Before you plug in"
  collapsible checklist that surfaces the data-cable, USB-hub,
  USB-debugging, "Trust this computer?", and unlock-the-screen items
  *before* the user has tried and failed, not after. Hidden once a device
  has been detected to avoid clutter.
- [x] **Smart terminal error suggestions** — `parseTerminalHints` in
  `useErrorGuide.js` matches 21 common terminal patterns and renders the
  matched hints above the raw log (TerminalOutput `terminal-error-hints`,
  `role="alert"`).
- [x] **Glossary keyboard access** — `GlossaryTip` is a `<button>` that
  opens on `@focus` (so Enter/Space-after-Tab works for free), closes on
  `@blur`, exposes `aria-expanded` + `aria-label` with the explanation
  text, and uses `role="tooltip"` on the popup. Touch tap calls the same
  toggle path.

### 10.5 Mobile & Responsive

- [x] **Terminal touch scrolling** — `.terminal` now uses
  `overscroll-behavior: contain` so over-scrolls at the top/bottom don't
  rubber-band into the page, and `overflow-x: auto` so wide unbreakable
  lines scroll horizontally instead of forcing layout shift. Line wrapping
  switched from `word-break: break-all` to `overflow-wrap: anywhere` so
  normal words don't break mid-word but very long tokens (CIDs, hashes)
  still wrap rather than overflowing silently.
- [x] **Header controls on small screens** — labels are already hidden
  below 600px (icon-only mode in `.header-btn-label`); the small-screen
  override that dropped buttons to 38×38 has been removed so all
  controls retain the WCAG 2.5.5 44×44 tap target. `row-gap` on the
  controls row makes the wrap (when buttons don't fit) read as two clean
  rows rather than visually crowding.
- [x] **Tap target sizing** — added a global `.btn-small` rule with
  `min-height: 44px` (the class was previously defined only in a
  StepIdentify scoped block, so 18 of 19 use sites had no styling).
  Header buttons restored to 44×44 below 600px. Spot-checked
  `.btn-link` (44px) and other primary classes — all already meet the
  target.

### 10.6 Search & Device Identification

- [x] **Relevance-ranked search results** — backend
  (`/api/devices/search`) already scores matches and sorts descending.
  Frontend now visually highlights the top result with a "Best match" tag
  and an accent left-border when there's more than one result, so users
  don't have to guess which row to pick.
- [x] **Explain disabled "Proceed" button** — StepIdentify renders a
  context-aware `proceed-hint` paragraph above the disabled Continue
  button ("Pick a category to continue", "Pick your device from the list",
  etc.), wired to the button via `aria-describedby` and announced via
  `aria-live="polite"`.
- [x] **ROM path validation** — manual ROM paths are validated in real time
  via `POST /api/validate-path` (debounced on input); StepSoftware and
  StepInstall both render a path-status line and disable the proceed
  button when the path is invalid.

---

## Phase 11 — Production Deployment & Security Hardening (deferred — future work)

*"If you ship it, harden it."*

> **Status (2026-05-09):** Deferred indefinitely after v0.2.0. OSmosis is
> currently a local-session tool: users start the web UI on `localhost`,
> flash a device, and shut it down. The "self-host on a Pi or home server,
> reachable from outside the LAN" use case this phase was designed for has
> not surfaced from real users yet. Building reverse proxies, fail2ban,
> privilege separation, and token auth against zero demand would be weeks
> of speculative work — better to wait for someone to actually try
> exposing OSmosis publicly and let their needs shape the design.
>
> **Re-open trigger:** any user-reported scenario of running OSmosis as
> an always-on service (workshop bench, classroom lab, repair shop,
> homelab dashboard) — at which point pull the relevant subsection back
> into the active roadmap.
>
> Items below are kept verbatim as a starting point for that future work,
> not as a current commitment.

### 11.1 Reverse Proxy & TLS — *future*

- [ ] `scripts/setup-nginx.sh` — auto-generate self-signed certs and configure
  nginx as a reverse proxy in front of Flask
- [ ] Let's Encrypt integration for public-facing instances (`certbot` automation)
- [ ] `make deploy` target that runs the full hardening stack in one shot

### 11.2 Firewall & Intrusion Prevention — *future*

- [ ] `scripts/setup-firewall.sh` — idempotent iptables/nftables script that
  opens only the ports OSmosis needs (443/5000 + USB passthrough)
- [ ] fail2ban jail for the web UI (rate-limit failed requests, block scanners)
- [ ] portsentry integration for network-exposed instances (optional)

### 11.3 Firmware Integrity Monitoring — *future*

- [ ] Scheduled checksum verification of cached firmware images (detect
  tampering between download and flash)
- [ ] Alert in the web UI when a cached image no longer matches its expected
  hash
- [ ] Config file integrity monitoring (hash-based, cron-triggered)

### 11.4 Privilege Isolation — *future*

- [ ] Run Flask as an unprivileged user; escalate only for flash operations
  (write to block devices, USB access)
- [ ] Clearly flag elevated operations in the UI ("this step requires root")
- [ ] Audit log of all privilege-escalated operations

### 11.5 Remote Access Hardening — *future*

- [ ] SSH tunnel documentation for remote OSmosis instances (avoid exposing
  HTTP directly)
- [ ] Optional token-based authentication for the web UI (generated on first
  run, no default credentials — ever)
- [ ] Rate limiting on all API endpoints

---

## Phase 12 — Post-Flash Automation & Device Orchestration

*"The flash is step one. Configuration is step two."*

Inspired by Ansible-based provisioning patterns. After flashing, many devices
need setup — Wi-Fi, locale, packages, hardening. OSmosis should handle that
too.

### 12.1 Resumable & Idempotent Flash Workflows

- [x] Workflows broken into discrete stages — `download → verify → backup →
  flash → post-configure` — implemented in
  [`web/workflow_engine.py`](../../web/workflow_engine.py) with persistent
  state under `~/.osmosis/workflows/<id>.json`
- [x] Resume from the last failed stage —
  `POST /api/workflows/<id>/resume?from=<stage>` (and the `from` parameter is
  optional; the server auto-picks the first non-completed stage)
- [x] Skip download if firmware is cached and checksum matches —
  `_stage_download` short-circuits when the cached file's SHA256 matches
  `expected_sha256`
- [x] Skip flash if device already reports the target firmware version —
  `_stage_flash` queries `adb shell getprop` for `ro.build.fingerprint` /
  `ro.build.display.id` / `ro.build.version.release` and marks the stage
  SKIPPED on match
  ([`tests/test_workflow_version_skip.py`](../../tests/test_workflow_version_skip.py))
- [x] Stage status tracking in the UI — completed / in-progress / failed /
  skipped, with per-stage Resume buttons, in
  [`frontend/src/components/shared/WorkflowTracker.vue`](../../frontend/src/components/shared/WorkflowTracker.vue)

### 12.2 Declarative Device Profiles

- [x] Structured YAML profile per device: firmware URL, checksum, flash tool,
  partition layout, required privileges, post-flash steps
  ([`web/device_profile.py`](../../web/device_profile.py), 284 profiles in
  [`profiles/`](../../profiles/))
- [x] Migration tool covers all six legacy `.cfg` files (devices,
  microcontrollers, scooters, ebikes, t2, medicat) via
  [`web/profile_migration.py`](../../web/profile_migration.py) — exposed at
  `POST /api/profiles/migrate` and idempotent (skips existing files)
- [x] Profile validation: required fields, category enum, firmware-type enum,
  support-status enum — `validate_all_profiles()` returns 0 errors across all
  284 profiles ([`tests/test_profile_migration.py`](../../tests/test_profile_migration.py))
- [x] Backend consumes profiles generically — `parse_devices_cfg`,
  `parse_microcontrollers_cfg`, `parse_scooters_cfg`, `parse_ebikes_cfg`,
  `parse_t2_cfg`, and `parse_medicat_cfg` now overlay `profiles/*.yaml` on
  top of legacy `.cfg`. Dropping a YAML file in `profiles/<category>/`
  registers a new device with no Python edits, and a profile with the same
  id as a `.cfg` row overrides it
  ([`tests/test_profile_route_integration.py`](../../tests/test_profile_route_integration.py))
- [x] Validator now operates from declarative `PROFILE_SCHEMA` /
  `FIRMWARE_SCHEMA` / `FLASH_STEP_SCHEMA` dicts using a JSON-Schema-shaped
  vocabulary (`type`, `required`, `enum`, `items`). Type-checks list/dict/bool
  fields and recurses into `firmware[]` and `flash_steps[]`. Kept dependency-free
  (no jsonschema/Pydantic added) — the schema dicts can be handed to either
  library later without rewriting

### 12.3 Post-Flash Configuration Engine

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

### 12.4 Dynamic Device Inventory

- [ ] Auto-detect USB/serial/BLE-connected devices and map them to device
  profiles (extend current ADB + USB VID detection)
- [ ] Network device discovery (mDNS/SSDP) for post-flash configuration of
  networked devices (routers, SBCs, IoT)
- [ ] Inventory view in the web UI showing all detected devices, their status,
  and available actions

### 12.5 Composed Workflows

- [x] "Flash + Configure" — `flash-and-configure` template in
  `WORKFLOW_TEMPLATES` (download → verify → backup → flash → post-configure)
- [x] "Configure only" — `configure-only` template (post-flash tasks only)
- [x] "Verify only" — `verify-only` template (download + verify, no flash)
- [x] User-defined workflow templates — `POST /api/workflows` accepts a
  `stages: ["download", "verify", ...]` array. Stages are validated against
  `STAGE_EXECUTORS` and run in the order given (e.g. `backup` before
  `download` is allowed if you want to capture state before grabbing fresh
  firmware) ([`tests/test_workflow_custom_stages.py`](../../tests/test_workflow_custom_stages.py))

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
| 4 | OTA Updates | Done | Scooter OTA, phone one-click update |
| 5 | Community | Done | Device search, submissions, IPFS manifests, config channels |
| 6 | New Devices | Partial | Fastboot, routers, consoles done; 13 new categories added (cameras, e-readers, TVs, vacuums, keyboards, synths, handhelds, etc.) |
| 7 | Platform | Done | YAML config, plugin architecture, PWA |
| 8 | Build Your OS | Done | 5 distros, IPFS layer caching, community gallery |
| 10 | Usability & Accessibility | Done | Multi-device picker, progress bars, error recovery, WCAG AA, mobile UX |
| 11 | Deployment & Security | Deferred (future) | Nginx + TLS, firewall, fail2ban, integrity monitoring, privilege isolation — re-open when self-hosting demand surfaces |
| 12 | Post-Flash Automation | Partial | 12.1, 12.2, 12.5 done (resumable/idempotent flash with version-skip, declarative YAML profiles powering 284 devices, composed workflows + user-defined stage chains); 12.3 (Ansible) and 12.4 (auto device inventory) still planned |

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
