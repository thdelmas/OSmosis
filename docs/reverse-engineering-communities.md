# Reverse Engineering & Custom Firmware Communities

A curated directory of communities, projects, and tools that share the Osmosis
philosophy: **you bought it, you own it**. These groups reverse-engineer,
unlock, and reflash consumer devices across every form factor — from scooters
to routers to electric bikes.

---

## Electric Scooters & Micromobility

### ScooterHacking.org

- Site: `https://scooterhacking.org/`
- GitHub: `https://github.com/scooterhacking`
- CFW Hub: `https://cfw.sh/`
- Discord, Telegram, GitHub

The reference community for Xiaomi and Ninebot custom firmware. Maintains CFW
builders for multiple models (Max G30, ESx, Pro 2), the ScooterHacking Utility
app, a firmware archive, and a documented API at `api.cfw.sh`. Reverse-
engineered the NinebotCrypto protocol. Active developer assembly on Discord.

### LibreScoot

- Site: `https://librescoot.org/`
- Discord

Open-source firmware for the unu Scooter Pro. Community-driven with active
Discord support. A good model for what a full FOSS scooter stack looks like.

### ScooterFlasher

- GitHub: `https://github.com/Encryptize/scooterflasher`

Simple OpenOCD wrapper for reflashing scooter firmware. Useful as a reference
for integrating low-level flash tooling.

### Endless Sphere DIY EV Forum

- Forum: `https://endless-sphere.com/`

Broad DIY electric vehicle community. Hosts threads on open-source M365
firmware (based on the EBiCS project) and general micromobility hacking.

---

## Electric Bikes

### OpenSource EBike Firmware (OSFW)

- Site: `https://opensourceebikefirmware.bitbucket.io/`

Flexible open-source firmware targeting e-bike motor controllers. Primarily
covers the TSDZ2 mid-drive kit. Community project started in 2017, now with
many contributors working on performance, new features, and new kit support.

### Syklo — Open Source E-Bike Kits

- Site: `https://syklo.fr/en/`

Chronicles the development of open-source firmware for electric bicycle kits.
Good documentation on the journey from reverse engineering to a working
open-source alternative.

### Pedelecs Forum — Lishui Controller Project

- Thread: `https://www.pedelecs.co.uk/forum/threads/lishui-controller-modification-firmware-flash-project.48938/`

Community effort to reverse-engineer and reflash Lishui motor controllers used
in many budget e-bikes. Forum-based, with detailed logs of the flash process.

---

## Vehicles (CAN Bus)

### Open Vehicles

- GitHub: `https://github.com/openvehicles`

Reverse engineering tools for vehicle systems based on CAN bus communications.
Targets OBD-II and proprietary vehicle protocols. Relevant to Osmosis's
long-term roadmap for cars and boats.

---

## Routers & Networking

### OpenWrt

- Site: `https://openwrt.org/`
- Firmware selector: `https://firmware-selector.openwrt.org/`

The gold standard of open-source router firmware. Fully FOSS, 3000+ packages,
massive community. Supports hundreds of router models. SquashFS/JFFS2
filesystem with the opkg package manager. A model for how a mature device
freedom project operates at scale.

### DD-WRT

- Site: `https://dd-wrt.com/`

Linux-based alternative router firmware. More end-user friendly than OpenWrt,
with a GUI-first approach. Based on OpenWrt kernel since v23 (2005). Supports
a wide range of brands (Linksys, Asus, Netgear, etc.).

### FreshTomato

- Wikipedia: `https://en.wikipedia.org/wiki/List_of_router_firmware_projects`

Fork of the Tomato router firmware. Another option in the alternative router
firmware ecosystem, focused on Broadcom-based routers.

---

## IoT & Smart Home

### Tasmota

- GitHub: `https://github.com/arendst/Tasmota`
- Docs: `https://tasmota.github.io/docs/Getting-Started/`

Alternative firmware for ESP8266 and ESP32 devices. WebUI configuration, OTA
updates, automation via timers/rules, entirely local control over MQTT, HTTP,
Serial, or KNX. Huge community. The poster child for "your smart home doesn't
need the cloud."

### ESPHome

- Site: `https://esphome.io/`

YAML-based firmware framework for ESP devices. Deep integration with Home
Assistant. Complementary to Tasmota — ESPHome is more declarative, Tasmota
more interactive.

---

## General Reverse Engineering Communities

### Hackaday.io

- RE projects: `https://hackaday.io/projects?tag=reverse+engineering`

96+ tagged reverse engineering projects. Ranges from Nokia phone firmware to
Sena headsets to LED panels to BBQ thermometers. Strong educational focus with
workshops and learning platforms. Good place to discover niche device RE
efforts.

### OFRAK

- Info: `https://ofrak.com/`

Open-source firmware analysis and modification framework. A neutral
investigative tool in the same space as Ghidra, IDA, and Binwalk, but
specifically built for firmware RE workflows.

### Attify Blog

- Blog: `https://blog.attify.com/tag/firmware-reverse-engineering/`

IoT security blog with firmware reverse engineering tutorials. Covers
extraction, emulation, and exploitation. Good learning resource for anyone
getting started with device RE.

---

## Key Tools for Firmware Reverse Engineering

| Tool | Type | License | Notes |
|------|------|---------|-------|
| Ghidra | Disassembler / Decompiler | Free (NSA) | Best free alternative to IDA |
| Binwalk | Firmware extraction | FOSS | Extract and analyze firmware images |
| Radare2 / Rizin | RE framework | FOSS | Scriptable, CLI-first |
| Frida | Dynamic instrumentation | FOSS | Runtime hooking and manipulation |
| JaDx | Android decompiler | FOSS | Decompile APKs to Java source |
| Firmware ModKit | Firmware repacking | FOSS | Extract, patch, repack firmware |
| OpenOCD | Debug/flash | FOSS | JTAG/SWD interface, used by ScooterFlasher |
| esptool | ESP flash tool | FOSS | Flash ESP8266/ESP32, already in Osmosis stack |

---

## Relevance to Osmosis

These communities validate Osmosis's core thesis: **any OS on any device**.
Each one has independently arrived at the same conclusion — that manufacturer
lockdowns are a problem worth solving with open tools and community effort.

Key patterns worth studying:

- **ScooterHacking** and **Tasmota** show how CFW builders with web UIs lower
  the barrier to entry — directly aligned with Osmosis's guided wizard approach.
- **OpenWrt** demonstrates what maturity looks like: a package manager, a
  firmware selector, and support for hundreds of devices.
- **LibreScoot** and **OSFW** prove that even niche hardware can sustain a
  healthy open-source firmware community.
- **Open Vehicles** maps to Osmosis's roadmap for cars and boats.

Where possible, Osmosis should integrate with or link to these communities
rather than duplicate their work. They are allies, not competitors.
