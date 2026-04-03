# Gap Analysis: What Osmosis Is Missing

Cross-reference of features found in ScooterHacking, OpenWrt, Tasmota, ESPHome,
DD-WRT, LibreScoot, Open Vehicles (OVMS), and OpenSource E-Bike Firmware against
what Osmosis currently offers.

---

## Critical Gaps (high impact, directly aligned with Osmosis's mission)

### 1. No CFW Builder / Firmware Patcher

**What others do:**
- ScooterHacking has per-model web-based CFW builders (max.cfw.sh, mi.cfw.sh,
  esx.cfw.sh) where users toggle patches, adjust parameters (speed limits, motor
  current, KERS, braking, cruise control), and download a ready-to-flash ZIP.
- OpenWrt's Firmware Selector lets users customize package lists and inject
  first-boot scripts before building a firmware image on-demand via their
  Attended Sysupgrade Server.
- Tasmota supports compile-time customization via `user_config_override.h`.

**What Osmosis does:** Downloads pre-built firmware and flashes it. No
customization, no patching, no parameter tuning before flash.

**Gap:** Osmosis has no way to let users modify firmware before flashing. For
scooters, this means we can't compete with ScooterHacking's core value prop.
For routers, we can't match OpenWrt's package selection. For phones, we can't
offer debloating at the image level (only post-install via ADB).

**Recommendation:** Build a modular CFW builder framework. Start with scooter
firmware patching (we already have the protocol layer), then generalize to
other device types.

---

### 2. No OTA / Post-Flash Update Path

**What others do:**
- Tasmota has built-in OTA from its web UI or a dedicated OTA server
  (ota.tasmota.com), with dev builds auto-deployed from CI.
- ESPHome does OTA after the first USB flash — all subsequent updates are
  wireless, with mandatory SHA256 authentication.
- LibreScoot supports OTA delta patches across three release channels (testing,
  nightly, stable).
- OpenWrt has Attended Sysupgrade that preserves user-customized packages.

**What Osmosis does:** One-shot flash. The update checker (`/api/updates`)
polls for new ROM versions, but re-flashing requires the full manual workflow
again.

**Gap:** Once a device is flashed, Osmosis loses contact with it. No OTA push,
no delta updates, no channel-based release management. Users must repeat the
entire flash process for every update.

**Recommendation:** For BLE-connected scooters, implement OTA update delivery.
For Android devices, explore a companion app that can trigger sideload. For
ESP devices, integrate Tasmota/ESPHome OTA patterns.

---

### 3. No On-Device Real-Time Configuration

**What others do:**
- ScooterHacking's SHFW allows real-time parameter changes (speed profiles,
  current curves, field weakening) from the Utility app over BLE — no
  re-flash needed.
- Tasmota's web UI lets you change any setting live (timers, rules, GPIO
  assignments, MQTT config).
- ESPHome recompiles and OTA-pushes a new firmware from edited YAML.
- OVMS has a built-in web app for live vehicle diagnostics, control, and
  configuration.

**What Osmosis does:** Scooter info read (`/api/scooter/info`) and flash
(`/api/scooter/flash`). No live parameter tweaking, no dashboard, no
real-time telemetry.

**Gap:** Osmosis is flash-and-forget. The most engaged users (scooter owners,
IoT tinkerers) want ongoing interaction with their devices, not a one-time
tool.

**Recommendation:** Add a live dashboard for BLE-connected scooters showing
speed, battery, temperature, trip data. Allow register writes for supported
parameters without full reflash.

---

### 4. No Device Database / Hardware Compatibility Table

**What others do:**
- OpenWrt maintains a "Table of Hardware" — a searchable, community-editable
  database of every supported device with specs, installation notes, and
  known issues.
- DD-WRT has a Router Database with automated support detection.
- ESPHome has devices.esphome.io with a growing catalog.
- Tasmota has a Device Templates Repository where the community contributes
  GPIO configurations per device.

**What Osmosis does:** `devices.cfg` and `scooters.cfg` are flat
pipe-delimited files with ~4 Samsung tablets and ~40 scooters. No search, no
community contributions, no per-device installation notes or known issues.

**Gap:** Users can't look up "is my device supported?" without reading config
files. No community-driven device database. No per-device notes, gotchas, or
hardware revision handling.

**Recommendation:** Build a searchable device database (web UI + API). Allow
community contributions. Include hardware revisions, known issues, and
installation specifics. Start with scooters (40+ models already in config)
and Samsung phones.

---

### 5. No Community Wiki / Knowledge Base

**What others do:**
- ScooterHacking runs a DokuWiki with protocol docs, hardware mod guides,
  motor specs, BMS flashing guides, ESC recovery procedures, and FAQs.
- OpenWrt's wiki is the gold standard — community-editable, per-device pages,
  layered by skill level.
- DD-WRT has the legendary "Peacock Thread" — an exhaustive safety FAQ that
  every user reads before flashing.

**What Osmosis does:** A manifesto, a visual identity doc, and one
device-specific link collection (SM-T805). No wiki, no community-editable
docs, no protocol documentation, no hardware mod guides.

**Gap:** All the tribal knowledge lives nowhere. Users who want to understand
what Osmosis does under the hood have to read source code. No equivalent of
the Peacock Thread for safety guidance.

**Recommendation:** Stand up a wiki (DokuWiki or similar). Seed it with
protocol documentation (we already reverse-engineered Ninebot/Xiaomi BLE),
device pages, and a safety FAQ. Make it community-editable.

---

## Important Gaps (medium impact)

### 6. No Browser-Based Flashing (Web Serial)

**What others do:**
- ESPHome's ESP Web Tools uses the Web Serial API to flash devices directly
  from the browser — no software install, auto-detects chipset, selects
  correct firmware variant.
- Tasmota Web Installer does the same for ESP devices.

**What Osmosis does:** Requires a local Flask server running on the user's
machine with system tools (Heimdall, ADB, etc.) installed.

**Gap:** For ESP/IoT devices on our roadmap, browser-based flashing is the
expected UX. Users shouldn't need to install Python + Flask + system deps
just to flash an ESP32.

**Recommendation:** For the ESP device category, integrate Web Serial flashing
as an alternative to the local server approach. Could be a standalone page
hosted on GitHub Pages.

---

### 7. No Companion Mobile App

**What others do:**
- ScooterHacking Utility (Android) — 1.2M downloads before Play Store removal.
  BLE scanning, flashing, live diagnostics, SHFW configuration.
- OVMS has native Android and iOS apps for remote vehicle monitoring.
- Tasmota doesn't need one (web UI is mobile-responsive).

**What Osmosis does:** Generates a Termux companion script
(`/api/companion-script`) and links to third-party tools. No native app.

**Gap:** Scooter users expect a mobile app — that's how they interact with
their scooters. The Termux script is a power-user workaround, not a product.

**Recommendation:** Consider a Flutter or React Native app for BLE scooter
operations. Alternatively, make the web UI work well as a PWA on mobile with
Web Bluetooth API support.

---

### 8. No Declarative Device Configuration (YAML/Template System)

**What others do:**
- ESPHome: entire device configuration in a single YAML file — sensors,
  switches, automations, OTA settings. Compiled to firmware automatically.
- Tasmota: Template system for GPIO pin mapping per device, community-
  contributed.
- OpenWrt: UCI (Unified Configuration Interface) — text-based config files
  with a CLI and web UI.

**What Osmosis does:** Pipe-delimited config files (`devices.cfg`,
`scooters.cfg`) with hardcoded fields. Configuration is per-preset, not
per-device-instance.

**Gap:** No structured, extensible configuration format. Adding a new device
type means editing a flat file. No way for users to define their own device
profiles or share configurations.

**Recommendation:** Move to YAML or TOML device definitions. Each device gets
a profile file with flash method, partitions, firmware sources, known issues,
and user-tunable parameters. Community-shareable.

---

### 9. No Firmware Archive / Version Repository

**What others do:**
- ScooterHacking maintains `firmware.scooterhacking.org` — a centralized
  archive of all original firmware files from all supported scooters, mirrored
  on GitHub.
- OpenWrt keeps every release available for download, with a firmware selector
  for each version.

**What Osmosis does:** Downloads firmware on-demand from external sources
(LineageOS API, SourceForge, eCloud). No local archive, no version history
beyond what's in the ROM finder.

**Gap:** If an upstream source goes down, users lose access. No ability to
downgrade to a specific known-good version. No firmware provenance tracking.

**Recommendation:** Mirror critical firmware files. At minimum, keep SHA256
hashes of every firmware Osmosis has ever flashed, so users can verify files
obtained from other sources. IPFS pinning (already partially implemented)
could serve as the archive backend.

---

### 10. No Recovery / Unbrick Procedures

**What others do:**
- ScooterHacking documents ESC recovery via ST-Link (ReFlasher tool),
  including chip UID extraction and activation.
- DD-WRT has detailed recovery guides for bricked routers (TFTP recovery,
  serial console, JTAG).
- OpenWrt documents failsafe mode and recovery procedures per device.

**What Osmosis does:** Dry-run mode, system drive detection, manual
confirmation prompts. But no documented recovery procedures if something goes
wrong. No failsafe mode.

**Gap:** The manifesto says "make the process as safe, guided, and reversible
as possible." But there's no "what to do if it goes wrong" guide. No
automated recovery workflows.

**Recommendation:** Document recovery procedures for each supported device
category. For scooters, integrate ST-Link recovery. For Samsung, document
Download Mode recovery. For routers (future), document TFTP failsafe.

---

## Nice-to-Have Gaps (lower priority but worth noting)

### 11. No MQTT / Home Automation Integration

OVMS, Tasmota, and ESPHome all integrate with MQTT and Home Assistant. For IoT
devices on Osmosis's roadmap, this will be expected. Not needed now, but
important when ESP/IoT support lands.

**See also:** [Gladys Assistant research](gladys-assistant.md) — a privacy-first,
local-only home automation platform (Apache 2.0) with 39+ integrations (Zigbee,
Matter, MQTT, Z-Wave). Philosophically aligned with Osmosis. Potential
downstream consumer: flash with Osmosis, manage with Gladys.

### 12. No Plugin / Extension Architecture

OVMS has a vehicle plugin system where community members develop support for
new vehicles. Tasmota has a Berry scripting language for custom logic. Osmosis
has no plugin or extension system — adding a new device type means modifying
core code.

### 13. No CAN Bus Tooling

OVMS includes CAN bus logging, OBD2 translation, DBC decoding, and reverse
engineering tools. If Osmosis pursues the car/boat roadmap seriously, CAN bus
support will be essential. Not a gap today, but a prerequisite for the vehicle
category.

### 14. No Crash Reporting / Telemetry

ESPHome has automatic crash handlers with cross-reboot backtrace capture.
Osmosis has session logging but no structured error reporting. When users hit
problems, there's no easy way to share diagnostic data.

### 15. No Multi-Language Documentation

Osmosis has i18n in the UI, but all documentation is English-only. Tasmota has
a German Telegram group. ScooterHacking has multi-language community channels.
As the user base grows internationally, localized docs will matter.

---

## Priority Matrix

| Gap | Impact | Effort | Priority |
|-----|--------|--------|----------|
| 1. CFW Builder / Firmware Patcher | Very High | High | P0 |
| 2. OTA Update Path | Very High | High | P0 |
| 3. Live Device Dashboard | High | Medium | P1 |
| 4. Device Database | High | Medium | P1 |
| 5. Community Wiki | High | Low | P1 |
| 6. Browser-Based Flashing | Medium | Medium | P2 |
| 7. Companion Mobile App | Medium | High | P2 |
| 8. YAML Config System | Medium | Medium | P2 |
| 9. Firmware Archive | Medium | Low | P2 |
| 10. Recovery Procedures | High | Low | P1 |
| 11. MQTT Integration | Low | Medium | P3 |
| 12. Plugin Architecture | Low | High | P3 |
| 13. CAN Bus Tooling | Low | High | P3 |
| 14. Crash Reporting | Low | Low | P3 |
| 15. Multi-Language Docs | Low | Medium | P3 |

---

## Summary

Osmosis has strong foundations: multi-protocol flashing, guided wizard UX,
ROM discovery, IPFS distribution, dry-run safety, and a clear manifesto.

The biggest gaps are all about **what happens around the flash**:

- **Before:** No firmware customization (CFW builder, package selection, patch
  toggles).
- **After:** No ongoing device relationship (OTA updates, live dashboard,
  real-time config).
- **Around:** No community knowledge layer (wiki, device database, recovery
  docs).

The projects we studied succeed not just because they flash firmware, but
because they build ecosystems. ScooterHacking's CFW builders, OpenWrt's
firmware selector, Tasmota's web UI, ESPHome's YAML workflow — these are all
expressions of the same idea: **the flash is just the beginning**.

Osmosis should evolve from a flashing tool into a device freedom platform.
