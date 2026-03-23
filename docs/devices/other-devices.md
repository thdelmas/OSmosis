# Other Devices

This page covers smaller device categories that do not warrant their own dedicated wiki pages. It documents open-source alternatives, community research, and OSmosis support status for agricultural equipment, mobility devices, satellite/CubeSat platforms, storage and GPU firmware tools, and medical device data access.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Supported** | Open-source firmware or tooling available. Tested workflow. |
| **Planned** | OSmosis wizard in development. Community tools work today. |
| **Research** | Community tools documented. No OSmosis wizard. |
| **Not supported** | Proprietary/locked. Listed for user awareness. |

---

## Agricultural Equipment

### John Deere

| System | Status | Notes |
|--------|--------|-------|
| John Deere precision ag systems (GreenStar, JDLink) | Not supported | Deere enforces firmware signing and requires dealer-only access via Service ADVISOR software. Independent repair requires a license. |
| John Deere engine ECU | Not supported | ECU tuning requires proprietary John Deere diagnostic tools. |

**Right to repair context:** John Deere has faced sustained legal and regulatory pressure over repair restrictions. In 2023, Deere signed a Memorandum of Understanding with the American Farm Bureau Federation committing to make repair tools more accessible. As of 2026, independent access to full diagnostic and reflash capability remains limited. The FTC has investigated Deere's repair restrictions; no consent order has been finalized.

There is no community-maintained open firmware for John Deere equipment. Users seeking precision ag functionality on their own hardware should consider AgOpenGPS (below).

### AgOpenGPS

[AgOpenGPS](https://agopengps.com/) is an open-source precision agriculture guidance system. It does not flash or replace tractor ECU firmware — instead, it is an independent guidance computer built from commodity hardware.

| Component | Hardware | Firmware/Software | Status |
|-----------|---------|------------------|--------|
| AgOpenGPS guidance computer | Arduino Due / Teensy 4.1 + GPS receiver | [AgOpenGPS](https://github.com/farmerbriantee/AgOpenGPS) | Research |
| Autosteer controller | Arduino Nano + motor driver | AgOpenGPS Arduino sketches | Research |
| PCB v4/v5 (community boards) | Custom PCB with Teensy 4.1 | AgOpenGPS | Research |

**What it provides:**

- RTK GPS-based guidance with sub-inch accuracy (with RTK base station)
- Auto-steer via a steering motor or hydraulic valve control
- Section control for sprayers and planters
- Works with virtually any tractor regardless of brand — connected only to the steering wheel and GPS antenna

### ArduPilot Agricultural Drones

[ArduPilot](https://ardupilot.org/) is an open-source autopilot platform used in agricultural spray drones and survey drones.

| Platform | Supported Hardware | Status |
|---------|-------------------|--------|
| ArduPilot Copter (ag spray drone) | Pixhawk, Cube Orange, Matek H743 | Research |
| ArduPilot Plane (fixed-wing survey) | Pixhawk, Cube Orange | Research |

ArduPilot ag drone support includes flow rate control for liquid spray payloads, terrain following, and waypoint-based field coverage patterns.

---

## Powered Wheelchairs & Mobility Devices

### Commercial Controllers

| System | Status | Notes |
|--------|--------|-------|
| Permobil / Quantum / Sunrise Medical powered wheelchairs | Not supported | Controllers are locked and require manufacturer programming tools. Modifying mobility device firmware has direct physical safety implications. |
| R-net, DXBUS, ACT joystick controllers | Not supported | Proprietary CAN-based systems. No open firmware. |

**Safety note:** Powered wheelchairs are medical devices. Their firmware controls safety-critical behavior including speed limiting, cliff detection, anti-tip, and tilt compensation. Modification without professional expertise can cause serious injury.

### SuperHouse Automation (Open Source Mobility)

[SuperHouse Automation](https://superhouse.tv/) has published open-source control systems for powered mobility devices under the names WMC, PWC, and MOAC.

| Project | Hardware | Status | Notes |
|---------|---------|--------|-------|
| WMC (Wheelchair Motor Controller) | Custom PCB, Arduino/ESP32 | Research | Open-source motor controller for DIY wheelchair builds |
| PWC (Powered Wheelchair Controller) | Custom PCB | Research | Full joystick + safety features |
| MOAC (Mother Of All Controllers) | ESP32-based | Research | Generalized open-source mobility controller |

These are **DIY/research projects** intended for custom wheelchair builds, not for modifying existing commercial wheelchairs. Documentation and schematics are published by SuperHouse on GitHub.

---

## Satellite & CubeSat Platforms

### ArduPilot CubeSat

[ArduPilot](https://ardupilot.org/) supports small satellite attitude control and telemetry systems.

| Platform | Status | Notes |
|---------|--------|-------|
| ArduPilot Blimp / ArduPilot on CubeSat ACS | Research | Attitude control system firmware for CubeSat-class spacecraft. Community project. |

### SatNOGS (Libre Space Foundation)

[SatNOGS](https://satnogs.org/) is an open-source, open-hardware global network of satellite ground stations run by the [Libre Space Foundation](https://libre.space/).

| Component | Hardware | Firmware | Status |
|-----------|---------|---------|--------|
| SatNOGS ground station rotator | Custom PCB (Arduino-based) | [SatNOGS Rotator Controller](https://gitlab.com/librespacefoundation/satnogs) | Research |
| SatNOGS client (Raspberry Pi) | Raspberry Pi 3/4 | [SatNOGS Client](https://gitlab.com/librespacefoundation/satnogs/satnogs-client) | Research |

SatNOGS provides a community-operated network for tracking and receiving data from amateur satellites. The ground station hardware is open source and assembl-able from community-documented designs.

### UPSat

[UPSat](https://upsat.gr/) was the first open-source satellite to reach orbit (QB50 mission, 2017). Its hardware, firmware, and software are fully open.

| Component | Status | Notes |
|-----------|--------|-------|
| UPSat OBC (On-Board Computer) firmware | Research | STM32-based. Full source published. |
| UPSat EPS (Electrical Power System) firmware | Research | Open source. |
| UPSat ADCS (Attitude Determination) firmware | Research | Open source. |

Source: [github.com/librespacefoundation/upsat-flight-software](https://github.com/librespacefoundation/upsat-flight-software)

### OreSat

[OreSat](https://www.oresat.org/) is Portland State University's open-source CubeSat program. All hardware designs and firmware are published.

| Program | Status | Notes |
|---------|--------|-------|
| OreSat0 (1U CubeSat) | Research | Launched 2023. Fully open hardware and software. |
| OreSat0.5 | Research | Follow-on mission. |
| OreSat1 | Research | In development. |

---

## Storage & GPU Firmware

### NVMe Drives

NVMe drives expose management commands via `nvme-cli`. This is not firmware replacement — it is configuration and diagnostics via the NVMe specification's standard command set.

| Tool | Platform | What It Does | Status |
|------|---------|-------------|--------|
| [nvme-cli](https://github.com/linux-nvme/nvme-cli) | Linux | Format, secure erase, identify, SMART, firmware log, vendor-specific commands | Research |

Common uses:

- `nvme smart-log` — read SMART health data
- `nvme format` — cryptographic erase (fast secure wipe)
- `nvme fw-download` + `nvme fw-activate` — update drive firmware (using manufacturer-supplied firmware files)
- `nvme sanitize` — hardware-level data sanitization

**Firmware source:** `nvme-cli` can download and apply firmware images, but the firmware images themselves must come from the drive manufacturer. There is no open-source replacement firmware for commodity NVMe drives.

### NVIDIA GPUs (nvflash)

| Tool | Purpose | Status |
|------|---------|--------|
| [nvflash](https://www.techpowerup.com/download/nvidia-nvflash/) | Flash NVIDIA GPU VBIOS | Research |

`nvflash` allows reading the current GPU VBIOS, flashing a different VBIOS (e.g. from a reference card to enable higher TDP limits), and recovering from a partially corrupted VBIOS. Use cases include:

- Flashing a desktop VBIOS onto a mobility GPU (for MXM modules in workstation laptops)
- Updating VBIOS when the manufacturer does not provide an installer for Linux
- Mining rig VBIOS modifications (reduced power draw, adjusted memory timings)

**Risk:** A failed VBIOS flash can prevent the GPU from displaying output. Recovery requires a second GPU or a backup VBIOS stored beforehand.

### AMD GPUs (AMDVBFlash)

| Tool | Purpose | Status |
|------|---------|--------|
| [AMDVBFlash](https://www.techpowerup.com/download/ati-atiflash/) | Flash AMD GPU VBIOS | Research |

`AMDVBFlash` (also known as `amdvbflash` on Linux) provides the same capabilities as nvflash for AMD Radeon GPUs: read, write, and verify VBIOS. Community VBIOS modifications for AMD GPUs are common in the mining community and for enabling features on OEM-locked cards.

---

## Medical Devices (Data Access Only)

**Important:** The entries below are **data access tools only**. They do not replace or modify medical device firmware. They run on separate hardware (a phone, PC, or Raspberry Pi) and communicate with the medical device to read data — typically via Bluetooth, NFC, or USB.

Modifying the firmware of medical devices is generally illegal without regulatory approval in most jurisdictions, and doing so could cause serious injury or death. OSmosis does not support or document firmware replacement for medical devices.

### CPAP / OSCAR

[OSCAR](https://www.sleepfiles.com/OSCAR/) (Open Source CPAP Analysis Reporter) reads therapy data from CPAP and BiPAP machines.

| Device Family | Data Access Method | Status |
|-------------|-------------------|--------|
| ResMed AirSense 10/11 | SD card data files | Research |
| Philips DreamStation | SD card data files | Research |
| Fisher & Paykel SleepStyle | SD card / Bluetooth | Research |

OSCAR reads the proprietary data files that CPAP machines write to their SD cards and produces detailed charts of AHI, leak rate, pressure, flow limitation, and snore index. No firmware is modified.

### OpenAPS / AndroidAPS (DIY Closed-Loop Insulin)

[OpenAPS](https://openaps.org/) and [AndroidAPS](https://androidaps.readthedocs.io/) are open-source artificial pancreas systems. They run on a separate computer (Raspberry Pi Zero, Android phone) and communicate with a CGM (continuous glucose monitor) and insulin pump to automate insulin delivery.

| Component | Runs On | Status |
|-----------|---------|--------|
| OpenAPS algorithm | Raspberry Pi / Intel Edison | Research |
| AndroidAPS | Android phone | Research |

**The insulin pump firmware is not modified.** The system communicates with compatible pumps (Medtronic 5xx/7xx series, Omnipod) via radio (OpenAPS) or Bluetooth (AndroidAPS with compatible pumps). The pump executes temporary basal rate commands issued by the algorithm.

Compatible pumps are older Medtronic models with known radio protocols. This is an advanced DIY medical project — see the [OpenAPS documentation](https://openaps.readthedocs.io/) for the extensive safety requirements.

### xDrip+ / Juggluco (CGM Data Access)

[xDrip+](https://github.com/NightscoutFoundation/xDrip) and [Juggluco](https://www.juggluco.nl/) are Android apps that communicate directly with CGM sensors without the manufacturer's app.

| CGM Sensor | Tool | Method | Status |
|-----------|------|--------|--------|
| Dexcom G5/G6/G7 | xDrip+ | Bluetooth | Research |
| Libre 2 / Libre 3 | xDrip+ / Juggluco | Bluetooth | Research |
| Medtronic Enlite | xDrip+ (via transmitter) | Radio bridge | Research |

These tools provide:

- Direct Bluetooth communication with the CGM sensor, bypassing the manufacturer app
- Local data storage without mandatory cloud accounts
- Integration with Nightscout, AndroidAPS, and other open-source diabetes management tools
- Glucose alarms and share features

**No firmware modification is involved.** xDrip+ and Juggluco are communication and display apps only.

---

## Links

| Resource | URL |
|---------|-----|
| AgOpenGPS | https://github.com/farmerbriantee/AgOpenGPS |
| ArduPilot | https://ardupilot.org/ |
| SatNOGS | https://satnogs.org/ |
| Libre Space Foundation | https://libre.space/ |
| UPSat flight software | https://github.com/librespacefoundation/upsat-flight-software |
| OreSat | https://www.oresat.org/ |
| SuperHouse Automation (open mobility) | https://superhouse.tv/ |
| nvme-cli | https://github.com/linux-nvme/nvme-cli |
| OSCAR (CPAP analysis) | https://www.sleepfiles.com/OSCAR/ |
| OpenAPS documentation | https://openaps.readthedocs.io/ |
| AndroidAPS documentation | https://androidaps.readthedocs.io/ |
| xDrip+ | https://github.com/NightscoutFoundation/xDrip |
| Juggluco | https://www.juggluco.nl/ |
