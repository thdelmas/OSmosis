# Electric Scooters

OSmosis supports flashing custom firmware (CFW) and stock firmware on electric scooters. Scooter firmware controls speed limits, acceleration curves, braking behavior, battery management, and dashboard settings.

**Important:** Modifying scooter firmware may void your warranty and can affect safety. Always understand the changes you're making. See the [Safety](../../web/routes/safety.py) routes for OSmosis's built-in safety checks.

---

## Protocols

Scooters communicate using one of two main protocols:

| Protocol | Header | Used by |
|----------|--------|---------|
| **Ninebot** | `0x5AA5` | Ninebot-branded scooters, newer Xiaomi models (1S, 3, Pro 2, Essential) |
| **Xiaomi** | `0x55AA` | Original Xiaomi M365 and Mi Pro |

OSmosis auto-detects the protocol based on the device selected.

## Flash Methods

| Method | Description | Used by |
|--------|-------------|---------|
| **BLE** | Bluetooth Low Energy firmware push from a phone or computer | Most Ninebot/Xiaomi models |
| **ST-Link** | SWD debug probe connected to the ESC board's programming header | ESC chip flashing (STM32/AT32) |
| **BLE + ST-Link** | BLE for dashboard/BMS, ST-Link for ESC | Most supported models |
| **UART** | Serial connection via TX/RX pads | Xiaomi Mi 4+, some newer models |

---

## Ninebot Max Series (SNSC 2.0/2.1)

The Ninebot Max is the most popular scooter for custom firmware. The G30 family has mature CFW support.

| Device | ID | Flash Method | CFW | SHFW | Notes |
|--------|----|-------------|-----|------|-------|
| Ninebot Max G30 | `nb-g30` | BLE + ST-Link | [max.cfw.sh](https://max.cfw.sh/) | Yes | STM32/AT32 ESC. **GD32 chips are not flashable.** |
| Ninebot Max G30P | `nb-g30p` | BLE + ST-Link | [max.cfw.sh](https://max.cfw.sh/) | Yes | G30 variant with Gen2 motor |
| Ninebot Max G30D | `nb-g30d` | BLE + ST-Link | [max.cfw.sh](https://max.cfw.sh/) | Yes | German edition (25 km/h speed limit) |
| Ninebot Max G30LP | `nb-g30lp` | BLE + ST-Link | [max.cfw.sh](https://max.cfw.sh/) | Yes | Lite/budget Max variant |
| Ninebot Max G2 | `nb-g2` | BLE + ST-Link | [cfw.sh](https://cfw.sh/) | Yes | Check chip first: GD32 = not flashable |
| Ninebot Max G3 | `nb-g3` | BLE + ST-Link | -- | Planned | SHFW not yet available |

### What is SHFW?

**SHFW (ScooterHacking Firmware)** is a community-developed custom firmware that patches the stock firmware with user-selected parameters. It allows:
- Speed limit removal or adjustment
- Custom acceleration and braking curves
- Motor power adjustments
- Dashboard display changes
- Region lock removal

### GD32 Warning

Some newer production runs replace the STM32 ESC chip with a GD32 clone. GD32 chips **cannot be flashed** with current tools. Before purchasing or attempting to flash, identify your ESC chip:
1. Open the scooter deck
2. Locate the ESC board
3. Read the chip marking — look for `STM32`, `AT32`, or `GD32`

---

## Ninebot F-Series / D-Series

Mid-range Ninebot scooters with growing CFW support.

| Device | ID | Flash Method | CFW | SHFW | Notes |
|--------|----|-------------|-----|------|-------|
| Ninebot F2 | `nb-f2` | BLE + ST-Link | [cfw.sh](https://cfw.sh/) | Yes | |
| Ninebot F2 Pro | `nb-f2pro` | BLE + ST-Link | [cfw.sh](https://cfw.sh/) | Yes | Check chip: GD32 = not flashable |
| Ninebot F3 | `nb-f3` | BLE + ST-Link | -- | Planned | |
| Ninebot F3 Pro | `nb-f3pro` | BLE + ST-Link | -- | Planned | |
| Ninebot D18 | `nb-d18` | BLE + ST-Link | [cfw.sh](https://cfw.sh/) | Yes | |
| Ninebot D28 | `nb-d28` | BLE + ST-Link | [cfw.sh](https://cfw.sh/) | Yes | |
| Ninebot D38 | `nb-d38` | BLE + ST-Link | [cfw.sh](https://cfw.sh/) | Yes | |

---

## Ninebot E-Series (SNSC 1.x)

The original Ninebot commuter scooter line. Well-supported by community CFW.

| Device | ID | Flash Method | CFW | SHFW | Notes |
|--------|----|-------------|-----|------|-------|
| Ninebot ES1 | `nb-es1` | BLE + ST-Link | [esx.cfw.sh](https://esx.cfw.sh/) | Yes | |
| Ninebot ES2 | `nb-es2` | BLE + ST-Link | [esx.cfw.sh](https://esx.cfw.sh/) | Yes | |
| Ninebot ES4 | `nb-es4` | BLE + ST-Link | [esx.cfw.sh](https://esx.cfw.sh/) | Yes | |
| Ninebot E22 | `nb-e22` | BLE + ST-Link | [cfw.sh](https://cfw.sh/) | Yes | |
| Ninebot E25 | `nb-e25` | BLE + ST-Link | [cfw.sh](https://cfw.sh/) | Yes | |
| Ninebot E45 | `nb-e45` | BLE + ST-Link | [cfw.sh](https://cfw.sh/) | Yes | |
| Ninebot E2 | `nb-e2` | BLE + ST-Link | -- | Planned | Similar to ES2 comms |

---

## Ninebot P/GT Series (Performance)

High-performance Segway-branded scooters. CFW support is in development.

| Device | ID | Flash Method | SHFW | Notes |
|--------|----|-------------|------|-------|
| Segway P65 | `nb-p65` | BLE + ST-Link | Planned | |
| Segway P100S | `nb-p100s` | BLE + ST-Link | Planned | |
| Segway GT1 | `nb-gt1` | BLE + ST-Link | Planned | |
| Segway GT2 | `nb-gt2` | BLE + ST-Link | Planned | |
| Segway GT3 | `nb-gt3` | BLE + ST-Link | Planned | |
| Segway ZT3 Pro | `nb-zt3pro` | BLE + ST-Link | Planned | |

---

## Ninebot T-Series

| Device | ID | Flash Method | SHFW | Notes |
|--------|----|-------------|------|-------|
| Ninebot Air T15 | `nb-t15` | BLE + ST-Link | Planned | |

---

## Xiaomi Scooters

Xiaomi scooters are manufactured by Ninebot. Older models (M365, Mi Pro) use the Xiaomi protocol; newer models use the Ninebot protocol.

### Classic Models (Xiaomi Protocol)

| Device | ID | Flash Method | CFW | SHFW | Notes |
|--------|----|-------------|-----|------|-------|
| Xiaomi M365 | `xi-m365` | BLE + ST-Link | [mi.cfw.sh](https://mi.cfw.sh/) | Yes | The original. Not the same as 1S. |
| Xiaomi Mi Pro | `xi-pro` | BLE + ST-Link | [mi.cfw.sh](https://mi.cfw.sh/) | Yes | |

### Ninebot-Protocol Models

| Device | ID | Flash Method | CFW | SHFW | Notes |
|--------|----|-------------|-----|------|-------|
| Xiaomi Essential | `xi-essential` | BLE + ST-Link | [mi.cfw.sh](https://mi.cfw.sh/) | Yes | Ninebot-made, uses Ninebot protocol |
| Xiaomi 1S | `xi-1s` | BLE + ST-Link | [mi.cfw.sh](https://mi.cfw.sh/) | Yes | Ninebot-made |
| Xiaomi 3 | `xi-3` | BLE + ST-Link | [mi.cfw.sh](https://mi.cfw.sh/) | Yes | Ninebot-made |
| Xiaomi Mi Pro 2 | `xi-pro2` | BLE + ST-Link | [pro2.cfw.sh](https://pro2.cfw.sh/) | Yes | |

### Xiaomi Mi 4+ Series (Newer, Locked)

These newer models use a different flashing approach and do not support SHFW.

| Device | ID | Flash Method | CFW | Notes |
|--------|----|-------------|-----|-------|
| Xiaomi Mi 4 | `xi-4` | UART | [mi-fw-info](https://mi-fw-info.streamlit.app/) | Use bw-flasher. ST-Link for Pro variant. |
| Xiaomi Mi 4 Lite | `xi-4lite` | UART | -- | Use bw-flasher |
| Xiaomi Mi 4 Pro | `xi-4pro` | ST-Link | -- | ST-Link required. Use scooterflasher. |
| Xiaomi Mi 4 Pro 2nd Gen | `xi-4pro2` | UART | -- | See wiki.bastelpichi.de/4pro2nd |
| Xiaomi Mi 4 Ultra | `xi-4ultra` | UART | -- | Use bw-flasher |
| Xiaomi Mi 5 | `xi-5` | UART | -- | BWFlasher stock only, CFW DFU verify fails |
| Xiaomi Mi 5 Pro | `xi-5pro` | UART | -- | See wiki.bastelpichi.de/brightway |

### Key Details for Xiaomi Mi 4+

- **No SHFW support:** These models use a new chipset that is not yet supported by ScooterHacking firmware.
- **bw-flasher:** A community tool for flashing via UART. Works for stock firmware and limited CFW.
- **DFU verification failures:** The Mi 5 rejects CFW during DFU verification. Only stock firmware can be flashed.

---

## Okai

Okai manufactures scooters used by rental companies (Lime, Tier, etc.). Flashing requires physical ST-Link access.

| Device | ID | Flash Method | SHFW | Notes |
|--------|----|-------------|------|-------|
| Okai ES100 | `okai-es100` | ST-Link | No | Rental scooter platform |
| Okai ES200 | `okai-es200` | ST-Link | No | |
| Okai ES400 | `okai-es400` | ST-Link | No | |
| Okai ES600 | `okai-es600` | ST-Link | No | |

---

## Pure

Popular UK/EU scooter brand. BLE protocol is under investigation.

| Device | ID | Flash Method | SHFW | Notes |
|--------|----|-------------|------|-------|
| Pure Air Pro | `pure-air-pro` | BLE | Planned | Popular in UK/EU, BLE protocol TBD |
| Pure Air Go | `pure-air-go` | BLE | Planned | Budget model |
| Pure Advance | `pure-advance` | BLE | Planned | Latest generation |

---

## NIU

NIU scooters are BLE-connected and app-locked. Community research is ongoing.

| Device | ID | Flash Method | SHFW | Notes |
|--------|----|-------------|------|-------|
| NIU KQi2 Pro | `niu-kqi2-pro` | BLE | Planned | BLE-connected, app-locked |
| NIU KQi3 Pro | `niu-kqi3-pro` | BLE | Planned | Higher speed variant |
| NIU KQi3 Max | `niu-kqi3-max` | BLE | Planned | Long-range variant |

---

## Navee

Budget scooter brand gaining popularity. Protocol suspected to be Ninebot-like.

| Device | ID | Flash Method | SHFW | Notes |
|--------|----|-------------|------|-------|
| Navee N65 | `navee-n65` | BLE | Planned | 65 km range, Ninebot-like protocol suspected |
| Navee S65 | `navee-s65` | BLE | Planned | Budget variant |

---

## Vsett (Performance)

Vsett scooters are popular in the enthusiast/performance segment with an active modding community.

| Device | ID | Flash Method | SHFW | Notes |
|--------|----|-------------|------|-------|
| Vsett 9+ | `vsett-9plus` | UART | Planned | Dual motor option, active modding community |
| Vsett 10+ | `vsett-10plus` | UART | Planned | Dual motor, sine wave controller |
| Vsett 11+ | `vsett-11plus` | UART | Planned | High-power dual motor |

---

## Dualtron / Minimotors (Performance)

Dualtron scooters are high-performance machines with proprietary Minimotors controllers.

| Device | ID | Flash Method | SHFW | Notes |
|--------|----|-------------|------|-------|
| Dualtron Thunder 2 | `dualtron-thunder-2` | UART | Planned | High-performance, proprietary controller |
| Dualtron Storm | `dualtron-storm` | UART | Planned | Flagship performance scooter |
| Dualtron Mini | `dualtron-mini` | UART | Planned | Entry-level Dualtron |

---

## General Notes

### Before Flashing

1. **Identify your hardware revision.** The same scooter model can have different ESC chips (STM32, AT32, GD32) across production batches.
2. **Check chip compatibility.** GD32 chips cannot be flashed with current tools.
3. **Back up your current firmware** using OSmosis's backup feature before making any changes.
4. **Understand the legal implications.** In many jurisdictions, removing speed limiters makes the scooter illegal for road use.

### CFW Generators

| Tool | URL | Scooters |
|------|-----|----------|
| ScooterHacking CFW | cfw.sh | Ninebot Max G2, F2, D-series, E-series |
| Max CFW | max.cfw.sh | Ninebot Max G30 family |
| ESx CFW | esx.cfw.sh | Ninebot ES1/ES2/ES4 |
| Mi CFW | mi.cfw.sh | Xiaomi M365, Pro, Essential, 1S, 3 |
| Pro 2 CFW | pro2.cfw.sh | Xiaomi Mi Pro 2 |

### Hardware Tools

| Tool | Purpose | Where to Buy |
|------|---------|-------------|
| **ST-Link V2** | SWD programmer for ESC chip flashing | AliExpress, Amazon, electronic component shops |
| **USB-UART adapter** | Serial connection for UART-flashed models | Same as above. Look for CP2102 or CH340. |
| **BLE adapter** | Bluetooth Low Energy for wireless flashing | Built into most laptops and phones |
