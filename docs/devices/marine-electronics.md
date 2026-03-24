# Boats & Marine Electronics

## Overview

Marine electronics include chart plotters, NMEA 2000 gateways, AIS transponders, and communication systems. The open-source marine ecosystem centers around **SignalK** (an open data standard for boats) and custom hardware running on Raspberry Pi or ESP32.

## Categories

### Chart Plotters & MFDs
Most commercial chart plotters (Garmin, Raymarine, Simrad) run proprietary firmware and are locked down. The open alternative is running **OpenCPN** or **AvNav** on a Raspberry Pi with a touchscreen.

**Status:** Research (commercial); Supported (RPi-based, via SBC workflow)

### NMEA 2000 Gateways
Open-source NMEA 2000 gateways like the **SH-ESP32** convert boat sensor data to WiFi/SignalK. These use ESP32 and are flashable via esptool.

**Status:** Planned (via microcontroller workflow)

### AIS Transponders
Open-source AIS receivers (dAISy, RTL-SDR based) can be configured or flashed.

**Status:** Research

### SignalK Server
A Raspberry Pi running **SignalK** acts as a boat's central data hub. Standard SD card imaging.

**Status:** Supported (via SBC workflow)

## Supported Devices

> This page is a stub. Device-specific guides will be added as OSmosis support expands.

| Device Type | Examples | Status |
|-------------|----------|--------|
| RPi chart plotter | OpenCPN, AvNav | Supported (SBC) |
| NMEA gateway | SH-ESP32 | Planned |
| AIS receiver | dAISy HAT | Research |
| SignalK hub | RPi + SignalK | Supported (SBC) |
| VHF radios | Commercial (locked) | Not supported |
