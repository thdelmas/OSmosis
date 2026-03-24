# Cars & Vehicle Electronics

## Overview

Vehicle electronics range from Android Auto head units (standard Android flashing) to OBD2 ECU tuning interfaces and Raspberry Pi-based dashboards. OSmosis aims to support the open and reflashable subset of this ecosystem.

## Categories

### Android Auto Head Units
Aftermarket head units running Android can be flashed via ADB sideload or SD card update, similar to phones/tablets. Stock Chinese head units often run outdated Android versions and benefit from community ROMs.

**Status:** Planned

### Raspberry Pi Dashboards
Raspberry Pi or SBC-based car computers (OBD2 readers, dashboards, dashcams) use standard SD card imaging.

**Status:** Supported (via SBC workflow)

### OBD2 & ECU Tuning
Devices like the OBDLink, ELM327, and open-source alternatives connect via Bluetooth or USB for diagnostics. ECU tuning (e.g. via KTuner, Tactrix OpenPort) is a specialized area.

**Status:** Research

### EV Chargers
Open-source EV charging stations (OpenEVSE) run on ESP32 or similar microcontrollers.

**Status:** Research (see also [Solar & Energy](solar-energy.md))

## Supported Devices

> This page is a stub. Device-specific guides will be added as OSmosis support expands.

| Device Type | Examples | Status |
|-------------|----------|--------|
| Android head units | Joying, Xtrons, Seicane | Planned |
| RPi dashboards | RetroPie Car, OBD-Pi | Supported (SBC) |
| OBD2 adapters | OBDLink, ELM327 clones | Research |
| EV chargers | OpenEVSE | Research |
