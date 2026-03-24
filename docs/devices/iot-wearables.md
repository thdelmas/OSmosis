# IoT & Wearable Devices

## Overview

IoT (Internet of Things) devices and wearables include smart home hardware, IP cameras, fitness trackers, and smartwatches. Many run on ESP32, ESP8266, or nRF52 chips and can be reflashed with open-source firmware.

## Categories

### Smart Home / Home Automation
Many smart plugs, bulbs, and switches use ESP8266/ESP32 chips internally and can be flashed with open firmware like **Tasmota** or **ESPHome** to work with Home Assistant without cloud dependencies.

| Firmware | Description |
|----------|-------------|
| [Tasmota](https://tasmota.github.io/) | Open firmware for ESP-based smart home devices |
| [ESPHome](https://esphome.io/) | YAML-configured firmware for ESP devices, integrated with Home Assistant |
| [WLED](https://kno.wled.ge/) | LED strip controller firmware for ESP32/ESP8266 |
| [OpenBeken](https://github.com/openshwprojects/OpenBK7231T_App) | Open firmware for Beken/Tuya-based devices |

**Status:** Planned (via microcontroller workflow)

### IP Cameras
Some IP cameras (Wyze, Yi, Xiaomi) run Linux internally and can be reflashed with **OpenIPC** or custom firmware for local-only operation.

| Firmware | Description |
|----------|-------------|
| [OpenIPC](https://openipc.org/) | Open-source IP camera firmware (HiSilicon, Ingenic, Sigmastar SoCs) |
| [Wyze RTSP](https://github.com/gtxaspec/wz_mini_hacks) | Custom firmware for local RTSP streaming |

**Status:** Research

### Wearables & Smartwatches
- **PineTime** — open-source smartwatch running InfiniTime, flashable via BLE OTA or SWD
- **Bangle.js** — JavaScript-powered smartwatch, programmable via Web Bluetooth
- **Fitbit / Apple Watch / Garmin** — proprietary, not supported

**Status:** Planned (PineTime, Bangle.js); Not supported (commercial wearables)

### Meshtastic / LoRa Devices
LoRa mesh networking devices running **Meshtastic** firmware on ESP32+LoRa boards (TTGO, Heltec, RAK). Flashable via USB serial.

**Status:** Planned (via microcontroller workflow)

## Supported Devices

> This page is a stub. Device-specific guides will be added as OSmosis support expands.

| Device Type | Examples | Status |
|-------------|----------|--------|
| ESP smart home | Sonoff, Tuya (ESP-based) | Planned |
| IP cameras | Wyze, Yi (OpenIPC) | Research |
| PineTime smartwatch | PineTime (InfiniTime) | Planned |
| Bangle.js | Bangle.js 2 | Planned |
| LoRa / Meshtastic | TTGO, Heltec, RAK | Planned |
| Fitbit / Apple Watch | Various | Not supported |
