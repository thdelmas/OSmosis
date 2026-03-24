# GPS & Navigation Devices

## Overview

Standalone GPS units from Garmin, TomTom, and others run proprietary firmware, but some models support custom maps, apps, or alternative firmware. Drone controllers and flight computers also fall into this category.

## Categories

### Garmin GPS
Garmin devices use a proprietary update mechanism (Garmin Express). Some older models allow custom map loading via SD card. Firmware modding is limited.

**Status:** Research

### TomTom GPS
Older TomTom units (GO series) ran a Linux-based OS and had an active modding community. Newer models are more locked down.

**Status:** Research

### Drone Controllers
Flight controllers (Betaflight, INAV, ArduPilot) run on STM32 boards and are flashable via USB DFU or serial. Ground station software and RC transmitters (EdgeTX/OpenTX) are also flashable.

**Status:** Planned

| Firmware | Devices | Flash Method |
|----------|---------|--------------|
| [Betaflight](https://betaflight.com/) | STM32 flight controllers | USB DFU |
| [INAV](https://github.com/iNavFlight/inav) | STM32 flight controllers | USB DFU |
| [ArduPilot](https://ardupilot.org/) | Pixhawk, CubeOrange | USB / SD card |
| [EdgeTX](https://edgetx.org/) | RadioMaster, Jumper RC transmitters | USB DFU / SD card |

### Handheld GPS / PLB
Devices like the Garmin inReach or ACR PLBs are fully proprietary and locked.

**Status:** Not supported

## Supported Devices

> This page is a stub. Device-specific guides will be added as OSmosis support expands.

| Device Type | Examples | Status |
|-------------|----------|--------|
| Drone flight controllers | Betaflight / INAV / ArduPilot | Planned |
| RC transmitters | EdgeTX / OpenTX radios | Planned |
| Garmin GPS | Various | Research |
| TomTom GPS | GO series | Research |
| Handheld PLB | Garmin inReach, ACR | Not supported |
