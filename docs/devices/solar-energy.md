# Solar & Energy Devices

OSmosis documents open-source firmware and monitoring solutions for solar inverters, battery management systems, EV chargers, and energy storage. An important distinction applies across almost all entries in this category:

> **Most solar/energy entries involve flashing or configuring a gateway, monitor, or sidecar device — not the inverter or battery itself.** The inverter firmware is almost never replaced. Instead, a separate ESP32 or Raspberry Pi-based device reads data from the inverter and provides local control and Home Assistant integration.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Supported** | Open-source toolchain available. OSmosis or community tools handle the flash. |
| **Planned** | OSmosis wizard in development. Manual tools exist today. |
| **Research** | Community solutions documented. Not yet wrapped in a wizard. |
| **Not supported** | Proprietary. No open firmware or integration path. |

---

## Hoymiles Microinverters (OpenDTU / AhoyDTU)

Hoymiles microinverters communicate with their cloud via a proprietary DTU (Data Transfer Unit) gateway. Two open-source ESP32-based gateway replacements exist: **OpenDTU** and **AhoyDTU**. You flash the ESP32 gateway, not the inverter.

### How It Works

```
Solar Panel → Hoymiles Microinverter → [RF 2.4GHz proprietary] → ESP32 (OpenDTU/AhoyDTU) → MQTT / Home Assistant
```

The ESP32 with a Nordic nRF24L01+ or CMT2300A radio module intercepts the same RF protocol the official DTU uses.

### Supported Inverter Families

| Inverter Series | RF Module Needed | OpenDTU | AhoyDTU | Notes |
|----------------|-----------------|---------|---------|-------|
| HM-series (HM-300, HM-350, HM-400, HM-600, HM-700, HM-800, HM-1000, HM-1200, HM-1500) | nRF24L01+ | Yes | Yes | Best-supported family |
| HMS-series (HMS-300, HMS-350, HMS-400, HMS-600, HMS-800, HMS-1000, HMS-1600, HMS-2000) | CMT2300A | Yes (OpenDTU-OnBattery) | Partial | Newer RF protocol |
| HMT-series (3-phase) | CMT2300A | Yes | Partial | |

### Gateway Hardware

| Gateway Board | Chip | Flash Method | Firmware |
|--------------|------|-------------|---------|
| ESP32 (any DevKit) + nRF24L01+ | ESP32 | esptool / OTA | [OpenDTU](https://github.com/tbnobody/OpenDTU) or [AhoyDTU](https://github.com/lumapu/ahoy) |
| OpenDTU-Fusion (dedicated PCB) | ESP32-S3 | esptool / OTA | OpenDTU |
| Wemos D1 Mini32 + nRF24L01+ | ESP32 | esptool / OTA | AhoyDTU |

### What OpenDTU / AhoyDTU Provides

- Real-time power, voltage, current, and temperature data from each microinverter
- MQTT publishing for Home Assistant, Node-RED, InfluxDB, etc.
- Web UI with per-inverter graphs
- Power limit control (reduce inverter output via RF commands)
- Zero-export control when combined with a power meter
- No Hoymiles cloud account required

### Status

| Component | Status |
|-----------|--------|
| ESP32 gateway firmware (OpenDTU) | Planned |
| ESP32 gateway firmware (AhoyDTU) | Planned |
| Hoymiles inverter firmware itself | Not supported |

---

## Victron Energy (Venus OS)

Victron Energy publishes [Venus OS](https://github.com/victronenergy/venus) — the Linux-based operating system for their GX devices (Cerbo GX, CCGX, Venus GX) — as open source. It can also be installed on a Raspberry Pi.

| Platform | Flash Method | Status |
|---------|-------------|--------|
| Victron Cerbo GX | OTA via VRM portal or SD card | Supported (official) |
| Victron CCGX | SD card image | Supported (official) |
| Raspberry Pi 2/3/4 (as GX device) | SD card image (`venus-raspi`) | Planned |
| Raspberry Pi Zero 2W | SD card image | Planned |

### What Venus OS Provides

- Monitoring and control for Victron inverters, MPPT solar charge controllers, BMV battery monitors, and more
- **VRM (Victron Remote Management):** Optional cloud portal; can be disabled for fully local operation
- **MQTT:** Local MQTT broker for Home Assistant and other automation systems
- **Node-RED:** Venus OS Large includes Node-RED for custom automation
- **Modbus TCP:** Exposes all Victron device data over Modbus for SCADA and BMS integration
- **Large image:** The `venus-large` variant adds Node-RED and SignalK server

### Venus OS Large (RPi)

Installing Venus OS on a Raspberry Pi turns it into a fully functional Victron GX device, providing the same monitoring capabilities as a Cerbo GX at lower hardware cost.

---

## Deye / Sunsynk Inverters (ESPHome RS485 Sidecar)

Deye and Sunsynk hybrid inverters (same hardware, different branding in different regions) expose all data and settings over RS485 Modbus. The standard integration uses an ESP32 or ESP8266 running ESPHome or a dedicated RS485-to-WiFi bridge.

**The inverter firmware is not replaced.** The ESP32 sidecar reads Modbus registers and publishes to MQTT / Home Assistant.

| Inverter Series | Interface | Sidecar Tool | Status |
|----------------|-----------|-------------|--------|
| Deye SUN-xK-SG04LP3 (low voltage, split-phase) | RS485 | ESPHome + RS485 adapter | Research |
| Deye SUN-xK-SG01LP1 (low voltage, single-phase) | RS485 | ESPHome + RS485 adapter | Research |
| Sunsynk 5kW / 8kW / 12kW | RS485 | [sunsynk Python library](https://github.com/kellerza/sunsynk) | Research |
| Deye / Sunsynk (grid-tie, no battery) | RS485 | ESPHome | Research |

### Hardware Required

| Component | Purpose |
|-----------|---------|
| ESP32 DevKit | Runs ESPHome |
| MAX485 or TTL-to-RS485 module | Level conversion for RS485 bus |
| 2-wire cable | Connects to inverter RS485 port |

### Key Details

- The RS485 port on Deye/Sunsynk is the same physical port used by the manufacturer's WiFi dongle.
- Remove or disable the manufacturer WiFi dongle if you want full local control without cloud interference.
- The Modbus register map is community-documented and covers battery SOC, grid power, PV power, load, and all settings.

---

## BMS (Battery Management Systems)

BMS units for lithium battery packs expose configuration and real-time data over BLE or UART. OSmosis and community tools support reading and configuring these units without full firmware replacement.

### JBD (Jiabaida) BMS

| Interface | Tool | Status |
|-----------|------|--------|
| BLE | [xiaoxiang BMS app](https://play.google.com/store/apps/details?id=com.xy.bms) (official) | Research |
| BLE | [overkillsolarBMS](https://github.com/FurTrader/OverkillSolarBMSTool) (Python) | Research |
| UART | Direct serial at 9600 baud, documented protocol | Research |

JBD BMS units are sold under many brand names (Overkill Solar, Daly-compatible, etc.). The BLE and UART protocol is community-documented. You can read cell voltages, temperatures, current, SOC, cycle count, and configure protection thresholds.

### Daly BMS

| Interface | Tool | Status |
|-----------|------|--------|
| UART / CAN | [daly-bms-cli](https://github.com/dreadnought/python-daly-bms) | Research |
| UART | Home Assistant Daly BMS integration | Research |

Daly BMS units use a documented UART protocol at 9600 baud. No firmware replacement is required or available — the protocol gives full read/write access to protection thresholds, balance settings, and real-time cell data.

### JK BMS

| Interface | Tool | Status |
|-----------|------|--------|
| BLE | [jkbms](https://github.com/syssi/esphome-jk-bms) (ESPHome component) | Research |
| RS485 | ESPHome RS485 component | Research |

JK BMS units are popular in DIY LiFePO4 builds. The ESPHome `jkbms` component reads all cell data and exposes it to Home Assistant.

### General BMS Notes

- **No firmware replacement:** BMS configuration is performed over the existing BLE/UART interface. The BMS firmware itself is not replaced.
- **Safety:** BMS protection thresholds (overvoltage, undervoltage, overcurrent) should be set conservatively. Incorrect configuration can cause battery damage or fire.

---

## OpenEVSE (EV Charger)

[OpenEVSE](https://openevse.com/) is a fully open-source Level 2 EV charger. The hardware design, firmware, and WiFi gateway are all open source.

| Component | MCU | Flash Method | Firmware | Status |
|-----------|-----|-------------|---------|--------|
| OpenEVSE controller board | ATmega328P | Arduino ISP / USB | [openevse/open_evse](https://github.com/OpenEVSE/open_evse) | Planned |
| OpenEVSE WiFi gateway | ESP32 | esptool / OTA | [openevse/ESP32_WiFi_V4.x](https://github.com/OpenEVSE/ESP32_WiFi_V4.x) | Planned |

### What OpenEVSE Provides

- J1772 Level 2 charging (up to 80A / 19.2kW)
- Local web interface for charge scheduling, energy monitoring, and current limiting
- MQTT and RAPI protocol for Home Assistant integration
- Solar divert mode: automatically adjusts charge rate to match available solar excess
- OCPP 1.6 support (optional) for smart charging network integration
- **Fully local operation** — no cloud dependency

### Key Details

- **Two separate MCUs:** The ATmega328P handles the safety-critical J1772 pilot signal and relay control. The ESP32 handles WiFi, the web UI, and Home Assistant integration. Both can be independently updated.
- **Commercial EVSE note:** Most commercial EV chargers (ChargePoint, Wallbox, Pulsar Plus, etc.) use proprietary firmware. They are not flashable. OpenEVSE is designed from the ground up for open hardware.

---

## Not Supported

| Device | Reason |
|--------|--------|
| Enphase microinverters | Encrypted firmware, no community access |
| SMA inverters | Proprietary. Some Modbus data access available. |
| Fronius inverters | Some Modbus/REST data access; no firmware replacement |
| Tesla Powerwall | Completely proprietary. No community firmware. |
| Growatt inverters | Cloud-dependent. Limited local access via unofficial tools. |
| Commercial EV chargers (ChargePoint, Wallbox, etc.) | Proprietary firmware |

---

## Links

| Resource | URL |
|---------|-----|
| OpenDTU | https://github.com/tbnobody/OpenDTU |
| AhoyDTU | https://github.com/lumapu/ahoy |
| Venus OS (Victron) | https://github.com/victronenergy/venus |
| Venus OS for Raspberry Pi | https://github.com/victronenergy/venus/wiki/raspberrypi-install |
| sunsynk Python library | https://github.com/kellerza/sunsynk |
| ESPHome JK BMS component | https://github.com/syssi/esphome-jk-bms |
| python-daly-bms | https://github.com/dreadnought/python-daly-bms |
| OpenEVSE firmware | https://github.com/OpenEVSE/open_evse |
| OpenEVSE WiFi firmware | https://github.com/OpenEVSE/ESP32_WiFi_V4.x |
