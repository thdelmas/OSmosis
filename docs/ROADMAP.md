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

## Phase 1 — Safety Net

*"If it can go wrong, we should have a guide for it."*

Goal: make Osmosis the safest way to flash any device. Before adding new
capabilities, ensure users can recover from failures.

### 1.1 Recovery & Unbrick Documentation

- [ ] Write per-device-category recovery guides:
  - Samsung: Download Mode recovery, Odin fallback, EFS restore
  - Scooters: ST-Link ESC recovery, BLE re-pair, chip UID extraction
  - Routers (future): TFTP failsafe, serial console, JTAG
  - ESP (future): serial reflash from known-good binary
- [ ] Create a "What went wrong?" troubleshooting wizard in the web UI
- [ ] Add a pre-flash checklist (battery level, backup status, correct image)

### 1.2 Firmware Verification & Archive

- [ ] Maintain a hash registry of every firmware Osmosis has ever flashed
  (SHA256 + device + version + source URL + date)
- [ ] Verify downloaded firmware against known hashes before flashing
- [ ] Expand IPFS pinning into a proper firmware archive with version history
- [ ] Allow users to pin and share verified firmware with the community
- [ ] Support firmware downgrade to a specific known-good version

### 1.3 Enhanced Backup

- [ ] Full NAND backup for Samsung devices (not just boot/recovery/EFS)
- [ ] Scooter firmware backup before flash (read current DRV/BLE/BMS images)
- [ ] One-click rollback to last backup
- [ ] Cloud/IPFS backup sync (optional, user-controlled)

---

## Phase 2 — CFW Builder

*"Don't just flash what others built — build your own."*

Goal: let users customize firmware before flashing. This is the single biggest
feature gap identified in the gap analysis.

### 2.1 Scooter CFW Builder (Web UI)

- [ ] Per-model patch builder inspired by ScooterHacking's CFW builders
- [ ] Toggleable patches with safe defaults (all off):
  - Speed limits (per mode: eco / drive / sport)
  - Motor current limits
  - KERS (regenerative braking) on/off and intensity
  - Cruise control delay and behavior
  - Region lock bypass
  - Direct Power Control (DPC) mode
- [ ] Parameter validation with safety warnings
- [ ] Save/load/share configurations (localStorage + export/import JSON)
- [ ] Generate firmware ZIP (encoded + raw + info.txt, zip3 format)
- [ ] Preview diff: show exactly what bytes changed vs. stock

### 2.2 E-Bike CFW Builder (Web UI)

- [ ] Per-controller firmware configurator (Bafang bbs-fw, TSDZ2 OSF, KT)
- [ ] Toggleable parameters with safe defaults:
  - Assist levels and power curves
  - Speed limits per mode
  - Motor / battery current caps
  - Throttle enable/disable and mapping
  - PAS sensitivity and torque sensor tuning
  - Regenerative braking strength
- [ ] Safety validation with warnings for out-of-range values
- [ ] Save/load/share configurations (JSON export/import)
- [ ] Generate flashable firmware binary from configuration
- [ ] Preview diff: show parameter changes vs. stock defaults
- [ ] Link to [e-bike research](ebike-research.md) for background

### 2.3 Phone ROM Customization

- [ ] Pre-flash debloat profile selection (remove carrier/OEM apps at image level)
- [ ] Privacy hardening presets (disable analytics, cloud backup, location history)
- [ ] GApps variant picker (pico, nano, micro, full) with size estimates
- [ ] Post-install script injection (like OpenWrt's uci-defaults)

### 2.4 Router/IoT Firmware Customization (future)

- [ ] OpenWrt package selection UI (inspired by firmware-selector.openwrt.org)
- [ ] First-boot script editor (Wi-Fi SSID, password, firewall rules)
- [ ] Tasmota template picker from community database

---

## Phase 3 — Live Device Dashboard

*"The flash is just the beginning."*

Goal: maintain an ongoing relationship with flashed devices. Monitor, configure,
and update without re-flashing.

### 3.1 Scooter Live Dashboard

- [ ] Real-time telemetry over BLE:
  - Speed, odometer, trip distance
  - Battery percentage, voltage, cell temperatures
  - Motor temperature, controller temperature
  - Error codes with human-readable descriptions
- [ ] Register read/write for supported parameters (no re-flash needed)
- [ ] Speed profile switching from dashboard
- [ ] Trip history with charts
- [ ] Battery health tracking over time

### 3.2 Phone Device Monitor

- [ ] Post-flash health check via ADB (boot success, services running, storage)
- [ ] Installed ROM version tracking
- [ ] Battery health monitoring
- [ ] Storage usage breakdown

### 3.3 IoT Device Dashboard (future)

- [ ] ESP device status via MQTT or HTTP
- [ ] Sensor readings, switch states, uptime
- [ ] OTA trigger from dashboard

---

## Phase 4 — OTA Updates

*"Flash once, update forever."*

Goal: eliminate the need to repeat the full flash workflow for every update.

### 4.1 Scooter OTA

- [ ] Check for CFW updates over BLE
- [ ] Delta patch support (minimize BLE transfer time)
- [ ] Update channel selection (stable / beta / nightly)
- [ ] Automatic rollback on flash failure (requires Phase 1.3 backup)

### 4.2 Phone Update Pipeline

- [ ] ROM update notification via the web UI (already partially works)
- [ ] One-click re-sideload with automatic backup
- [ ] Companion app (Termux-based or standalone) for on-device update checks

### 4.3 ESP/IoT OTA (future)

- [ ] Push firmware to ESP devices over Wi-Fi (Tasmota/ESPHome pattern)
- [ ] SHA256-authenticated OTA (ESPHome model)
- [ ] Multi-device fleet updates

---

## Phase 5 — Device Database & Community

*"If it has a chip and a flash method, it belongs here."*

Goal: build the community layer that turns Osmosis from a tool into an
ecosystem.

### 5.1 Searchable Device Database

- [ ] Web UI: searchable, filterable device catalog
- [ ] API: `GET /api/devices/search?q=...` with full-text search
- [ ] Per-device pages with:
  - Hardware specs and revisions
  - Supported firmware / ROMs
  - Flash method and instructions
  - Known issues and gotchas
  - Community links (XDA, forums, wikis)
- [ ] Migrate `devices.cfg` and `scooters.cfg` to structured YAML/JSON

### 5.2 Community Contributions

- [ ] Submit new device profiles via web form or pull request
- [ ] Community-rated firmware configurations (like Tasmota Templates)
- [ ] User-submitted recovery stories and troubleshooting tips
- [ ] "Works with Osmosis" badge for verified device + firmware combos

### 5.3 Community Wiki

- [ ] Deploy a wiki (DokuWiki or similar) at wiki.osmosis.dev (or equivalent)
- [ ] Seed with:
  - Ninebot BLE protocol documentation (from our scooter_proto.py)
  - Xiaomi protocol documentation
  - Samsung Download Mode / Heimdall reference
  - Safety FAQ ("Peacock Thread" equivalent)
  - Per-device installation walkthroughs
- [ ] Make it community-editable with moderation

---

## Phase 6 — New Device Families

*"Every platform, every form factor."*

Goal: expand beyond Samsung phones and scooters to deliver on the manifesto's
promise.

### 6.1 fastboot Devices (high demand)

- [ ] Google Pixel (GrapheneOS, CalyxOS, LineageOS)
- [ ] OnePlus (LineageOS, Paranoid Android)
- [ ] Xiaomi (LineageOS, Pixel Experience)
- [ ] Fairphone (/e/OS, LineageOS)
- [ ] Bootloader unlock guidance per OEM

### 6.2 ESP32 / IoT

- [ ] esptool integration for serial flashing
- [ ] Browser-based flashing via Web Serial API (ESP Web Tools pattern)
- [ ] Tasmota and ESPHome as first-class flash targets
- [ ] Chipset auto-detection (ESP8266 vs ESP32 vs ESP32-S2/S3/C3)

### 6.3 Routers & Networking

- [ ] OpenWrt as primary flash target
- [ ] TFTP flash method
- [ ] Web UI flash method (upload to stock router admin page)
- [ ] Factory vs. sysupgrade image distinction
- [ ] DD-WRT and FreshTomato as alternatives

### 6.4 Game Consoles

- [ ] Nintendo Switch: RCM payload injection, Hekate bootloader, Atmosphere CFW
- [ ] Steam Deck: dual-boot setup, HoloISO/Bazzite
- [ ] PS Vita: HENkaku/Enso CFW

### 6.5 Single-Board Computers

- [ ] Raspberry Pi: SD card imaging, rpiboot
- [ ] Orange Pi / Banana Pi: Armbian, DietPi
- [ ] NVIDIA Jetson: sdkmanager integration

### 6.6 Electric Bikes

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

### 6.7 Vehicles (research)

- [ ] CAN bus read/write tooling (prerequisite)
- [ ] OBD2 diagnostics (leverage OVMS patterns)
- [ ] NMEA 2000 / SignalK for marine
- [ ] ECU tuning (long-term research)

---

## Phase 7 — Platform Maturity

*"The right amount of complexity is the minimum needed."*

Goal: the infrastructure that lets Osmosis scale without becoming a monolith.

### 7.1 Configuration System

- [ ] Replace pipe-delimited config with YAML device profiles
- [ ] Per-device-instance configuration (not just per-model)
- [ ] Export/import/share device profiles
- [ ] Template system for common flash patterns

### 7.2 Plugin Architecture

- [ ] Define a device driver interface (detect, flash, backup, monitor, update)
- [ ] Each device family as a plugin (Samsung, scooter, ESP, router, etc.)
- [ ] Community plugins for niche devices
- [ ] Plugin registry and discovery

### 7.3 Mobile App

- [ ] PWA (Progressive Web App) as first step — web UI with Web Bluetooth
- [ ] Native app if PWA limitations block key features (BLE background scanning)
- [ ] Feature parity with web UI for scooter operations
- [ ] Push notifications for update availability

### 7.4 Integrations

- [ ] MQTT broker support (for IoT device management)
- [ ] Home Assistant discovery (for ESPHome/Tasmota devices)
- [ ] Structured error reporting and crash telemetry (opt-in)
- [ ] Multi-language documentation

---

## Phase 8 — Build Your OS

*"Don't just flash an OS — build one from scratch."*

Goal: provide a graphical interface for assembling complete operating system
images — from fully automated Linux From Scratch builds to customized Ubuntu
installations with preseed. Users pick a base, configure it visually, and get a
flashable image out the other end.

### 8.1 Base Image Selection

- [ ] Chooser UI with three build paths:
  - **From scratch (LFS)** — automated Linux From Scratch pipeline
  - **From base** — start from Ubuntu, Debian, Arch, Alpine, or Void
  - **From template** — community-shared OS profiles (kiosk, NAS, router, etc.)
- [ ] Target architecture picker (x86_64, aarch64, armhf, riscv64)
- [ ] Target device picker (bare metal, VM, Raspberry Pi, custom SBC)

### 8.2 LFS Automated Builder

- [ ] Full Linux From Scratch build pipeline driven from the web UI
- [ ] Step-by-step progress visualization (toolchain, base system, configuration)
- [ ] Package selection UI: kernel, init system, shell, coreutils, networking
- [ ] Kernel configuration editor (graphical `menuconfig` equivalent)
- [ ] Cross-compilation support for building on x86 targeting ARM/RISC-V
- [ ] Build caching and incremental rebuilds (avoid multi-hour full rebuilds)
- [ ] Build log streaming to the web UI in real time
- [ ] Reproducible builds: pin every source tarball hash, export build manifest

### 8.3 Base Distro Customization (Ubuntu + Preseed & Friends)

- [ ] Ubuntu/Debian preseed generator:
  - Locale, timezone, keyboard layout
  - Disk partitioning scheme (auto / manual / LVM / encrypted LUKS)
  - User accounts and SSH key injection
  - Package selection and PPA/repo additions
  - Post-install script editor
- [ ] Arch Linux: automated `pacstrap` profile with package list and chroot scripts
- [ ] Alpine Linux: `setup-alpine` answer file generator
- [ ] Kickstart file generator for Fedora/RHEL-family (future)
- [ ] cloud-init config generator for VM/cloud targets (future)

### 8.4 Graphical Image Compositor

- [ ] Visual layer editor: base image + overlays (packages, configs, scripts)
- [ ] File manager for the target filesystem (add/remove/edit files before build)
- [ ] Service manager: enable/disable systemd/OpenRC units
- [ ] Firewall rule editor (iptables/nftables presets)
- [ ] Network configuration (static IP, Wi-Fi, VPN, bridge)
- [ ] Theming: wallpaper, display manager, default DE/WM selection

### 8.5 Build & Output

- [ ] Build engine: debootstrap, pacstrap, or LFS toolchain running in isolated
  container (Podman/Docker) or chroot
- [ ] Output formats:
  - Raw disk image (.img) — for dd / Osmosis USB writer
  - ISO (bootable live/installer)
  - Raspberry Pi SD card image
  - Vagrant box / OVA (VM targets)
  - rootfs tarball (for containers or manual deployment)
- [ ] Image size estimation before build
- [ ] Post-build validation: boot test in QEMU, filesystem integrity check
- [ ] Publish to IPFS or export for local flashing via Osmosis Phase 0 tools

### 8.6 Profiles & Sharing

- [ ] Save/load OS build profiles (JSON export/import)
- [ ] Community profile gallery: browse and fork others' builds
- [ ] Diff two profiles to see what changed
- [ ] Version-controlled profile history (git-backed)

---

## Phase Summary

| Phase | Theme | Key Deliverable | Depends On |
|-------|-------|-----------------|------------|
| 0 | Foundations | Flash tool (done) | — |
| 1 | Safety Net | Recovery docs, firmware archive, enhanced backup | — |
| 2 | CFW Builder | Scooter + e-bike firmware customization, ROM profiles | Phase 1 |
| 3 | Live Dashboard | Real-time scooter telemetry and config | — |
| 4 | OTA Updates | Wireless update delivery | Phase 1 + 3 |
| 5 | Community | Device database, wiki, contributions | Phase 1 |
| 6 | New Devices | fastboot, ESP, routers, e-bikes, consoles, SBCs, vehicles | Phase 5 + 7 |
| 7 | Platform | YAML config, plugins, mobile app, integrations | Phase 5 |
| 8 | Build Your OS | LFS builder, preseed generator, image compositor | Phase 0 + 7 |

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
