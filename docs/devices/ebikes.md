# E-Bike Controllers

OSmosis supports flashing open-source firmware on e-bike motor controllers and displays. This page covers every supported controller, compatible firmware projects, flash methods, and proprietary systems listed for awareness.

**Important:** Modifying e-bike firmware affects motor behavior, battery management, and safety systems. Incorrect firmware settings can cause overheating, battery damage, or loss of braking. Always test changes in a safe environment.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Supported** | Open-source firmware available. Flashing workflow tested. |
| **Experimental** | Firmware exists but has limited testing or partial feature support. |
| **Planned** | Controller recognized by OSmosis. Open firmware in development or not yet available. |
| **Not supported** | Proprietary/locked system. Listed for user awareness only. |

---

## Bafang Mid-Drive Motors

Bafang is the largest e-bike motor manufacturer. The BBSHD and BBS02 are the most popular targets for open-source firmware.

### Supported Models (STM8S-based)

| Device | Controller | Wattage | Flash Method | Firmware | Status |
|--------|-----------|---------|-------------|----------|--------|
| Bafang BBSHD 1000W | `bafang-bbshd` | 48V 1000W | ST-Link | [bbs-fw](https://github.com/danielnilsson9/bbs-fw) | Supported |
| Bafang BBSHD 48V 30A | `bafang-bbshd` | 48V 30A | ST-Link | [bbs-fw](https://github.com/danielnilsson9/bbs-fw) | Supported |
| Bafang BBS02B 750W | `bafang-bbs02` | 48V 750W | ST-Link | [bbs-fw](https://github.com/danielnilsson9/bbs-fw) | Supported |
| Bafang BBS02B 500W | `bafang-bbs02` | 48V 500W | ST-Link | [bbs-fw](https://github.com/danielnilsson9/bbs-fw) | Supported |
| Bafang BBS01B 350W | `bafang-bbs02` | 36V 350W | ST-Link | [bbs-fw](https://github.com/danielnilsson9/bbs-fw) | Experimental |

### What bbs-fw Provides

[bbs-fw](https://github.com/danielnilsson9/bbs-fw) is an open-source replacement firmware for Bafang BBS controllers that provides:

- Configurable pedal assist levels (speed and torque)
- Street-legal and off-road profiles
- Adjustable speed limits per assist level
- Throttle configuration (voltage curves, start speed)
- Walk assist mode
- Temperature-based throttling
- Configurable via a companion Android/desktop app over UART

### CAN Bus Models (Planned)

Newer Bafang motors use a CAN bus controller instead of the STM8S. Open-source firmware does not yet exist for these.

| Device | Controller | Wattage | Flash Method | Status | Notes |
|--------|-----------|---------|-------------|--------|-------|
| Bafang M500 | `bafang-m500` | 250-750W | UART | Planned | CAN bus. No open firmware yet. |
| Bafang M600 | `bafang-m600` | 500-1000W | UART | Planned | CAN bus. No open firmware yet. |
| Bafang M620 Ultra | `bafang-m620` | 1000-1500W | UART | Planned | Popular eMTB motor. CAN bus. No open firmware yet. |

### Key Details

- **MCU:** STM8S (supported models). Flashed via ST-Link SWD interface.
- **ST-Link connection:** Open the motor housing, locate the 4-pin SWD header (GND, SWDIO, SWCLK, 3.3V), and connect the ST-Link.
- **BBSHD vs BBS02:** Same firmware (bbs-fw), different power ratings. BBSHD handles higher current.
- **BBS01B:** Older model with limited testing under bbs-fw. Use with caution.
- **Risk:** Flashing erases the stock firmware. If the flash fails partway through, the motor is bricked until successfully reflashed.

---

## Tongsheng TSDZ2

The TSDZ2 is a torque-sensing mid-drive motor with a strong open-source community. It's the only mid-drive with both open controller firmware and open display firmware.

### Controllers

| Device | Board Revision | Flash Method | Firmware | Status |
|--------|---------------|-------------|----------|--------|
| TSDZ2 (V1 controller) | V1 | ST-Link | [TSDZ2-OSF](https://opensourceebikefirmware.bitbucket.io/) | Supported |
| TSDZ2 (V2 controller) | V2 | ST-Link | [TSDZ2-OSF](https://opensourceebikefirmware.bitbucket.io/) | Supported |

### Display Combos

| Combo | Display | Flash Method | Firmware | Status |
|-------|---------|-------------|----------|--------|
| TSDZ2 + VLCD5 | VLCD5 LCD | ST-Link | [TSDZ2-OSF](https://opensourceebikefirmware.bitbucket.io/) | Supported |
| TSDZ2 + 850C | 850C Color | ST-Link | [TSDZ2-OSF](https://opensourceebikefirmware.bitbucket.io/) | Supported |
| TSDZ2 + 860C | 860C Color | ST-Link | [TSDZ2-OSF](https://opensourceebikefirmware.bitbucket.io/) | Supported |

### What TSDZ2-OSF Provides

The [Open Source Firmware](https://opensourceebikefirmware.bitbucket.io/) project provides:

- True torque-sensing pedal assist (the TSDZ2's key differentiator)
- Configurable assist levels, current limits, and speed limits
- Battery management with low-voltage cutoff
- Field weakening for higher speed at the cost of efficiency
- Advanced telemetry on compatible displays (850C, 860C)
- Walk assist mode
- Street mode (for legal compliance) and off-road mode

### TSDZ8 (Next Generation)

| Device | Flash Method | Status | Notes |
|--------|-------------|--------|-------|
| TSDZ8 | ST-Link | Planned | Successor to TSDZ2. Open firmware in early development. |

### Key Details

- **MCU:** STM8S for both controller and displays
- **Flashing both:** You typically flash both the motor controller and the display. OSmosis handles both in one workflow.
- **860C recommended:** The 860C is the latest display with the best telemetry features. Recommended for new builds.
- **V1 vs V2:** Check the controller board inside the motor to identify the revision. Both are supported but use different firmware binaries.

---

## Kunteng (KT) Sine Wave Controllers

Kunteng controllers are common in hub motor e-bike conversions. The open-source firmware provides sine wave commutation (smoother, quieter operation than square wave).

### Controllers

| Device | Voltage | Flash Method | Firmware | Status |
|--------|---------|-------------|----------|--------|
| KT 36V Sine Wave | 36V | ST-Link | [stancecoke](https://github.com/stancecoke/BMSBattery_S_controllers_firmware) | Supported |
| KT 48V Sine Wave | 48V | ST-Link | [stancecoke](https://github.com/stancecoke/BMSBattery_S_controllers_firmware) | Supported |

### Displays

| Display | Flash Method | Firmware | Status |
|---------|-------------|----------|--------|
| KT-LCD3 | ST-Link | [stancecoke](https://github.com/stancecoke/BMSBattery_S_controllers_firmware) | Supported |
| KT-LCD5 | ST-Link | [stancecoke](https://github.com/stancecoke/BMSBattery_S_controllers_firmware) | Experimental |

### Key Details

- **MCU:** STM8S
- **Sine wave vs square wave:** Stock KT controllers use square wave commutation. The open firmware enables sine wave, which reduces motor noise and vibration.
- **KT-LCD5:** Newer display with partial firmware support. KT-LCD3 is fully supported.

---

## VESC-Based Controllers

VESC (Vedder Electronic Speed Controller) is an open-source, open-hardware motor controller platform. VESC controllers use Field Oriented Control (FOC) for maximum efficiency and smooth operation.

| Device | Hardware Version | Flash Method | Firmware | Status |
|--------|-----------------|-------------|----------|--------|
| VESC 4.x | 4.x | USB | [VESC Project](https://vesc-project.com/) | Supported |
| VESC 6.x | 6.x | USB | [VESC Project](https://vesc-project.com/) | Supported |
| VESC 75/300 | High-power | USB | [VESC Project](https://vesc-project.com/) | Supported |
| Flipsky VESC 75100 | Clone | USB | [VESC Project](https://vesc-project.com/) | Supported |
| Flipsky Mini FSESC 6.7 | Clone | USB | [VESC Project](https://vesc-project.com/) | Supported |

### What VESC Provides

- **FOC (Field Oriented Control):** Smooth, efficient, quiet motor operation
- **HFI (High Frequency Injection):** Sensorless operation at zero speed (VESC 6+)
- **VESC Tool:** Desktop configuration app (motor detection, PID tuning, throttle curves, battery limits, etc.)
- **App support:** ADC (throttle), PPM (RC), UART (display), NRF (remote), CAN bus
- **Data logging:** Real-time telemetry (voltage, current, temperature, speed, distance)
- **Multi-motor:** CAN bus linking for dual-motor setups

### Key Details

- **Not e-bike specific:** VESC is used in e-bikes, e-skateboards, electric go-karts, robots, and more.
- **USB configuration:** Plug in via USB, open VESC Tool, and configure everything. No SWD/ST-Link needed.
- **Flipsky clones:** Cheaper alternatives to official VESC hardware. Fully compatible with VESC firmware.
- **VESC 75/300:** High-voltage (75V) high-current (300A) variant for powerful builds.

---

## Other Controllers

### Lishui FOC Controller

| Device | Flash Method | Status | Notes |
|--------|-------------|--------|-------|
| Lishui FOC Controller | ST-Link | Experimental | Community-modded FOC firmware. See [Pedelecs forum thread](https://www.pedelecs.co.uk/forum/threads/lishui-controller-modification-firmware-flash-project.48938/). |

### CYC Aftermarket Mid-Drives

| Device | Flash Method | Status | Notes |
|--------|-------------|--------|-------|
| CYC X1 Pro | UART | Experimental | Aftermarket mid-drive. VESC-compatible controller option. |
| CYC X1 Stealth | UART | Experimental | Compact variant. |

---

## Proprietary / Locked Systems (Info Only)

These motor systems have **no open-source firmware**. They are listed so users understand why OSmosis cannot flash them and what alternatives exist.

| Motor | Brand | Controller | Why Locked | Alternative |
|-------|-------|-----------|------------|-------------|
| Bosch Performance CX | Bosch | Proprietary CAN | Encrypted firmware, locked bootloader | Third-party tuning dongles (SpeedBox, BadassBox) |
| Bosch Performance SX | Bosch | Proprietary CAN | Same as CX | Same dongles |
| Shimano EP8 | Shimano | Proprietary | Encrypted, no debug interface | Third-party dongles only |
| Shimano EP801 | Shimano | Proprietary | Same as EP8 | Same dongles |
| Yamaha PW-S2 | Yamaha | Proprietary | Encrypted | No known tuning options |
| Brose S Mag | Brose | Proprietary | Used by Specialized, Trek, etc. Encrypted. | SpeedBox dongle for some models |

### What "Tuning Dongles" Do

Tuning dongles for locked systems sit between the speed sensor and the motor controller. They manipulate the speed signal to trick the controller into thinking the bike is going slower than it is. This:
- Does **not** change the firmware
- Does **not** unlock the motor's full power
- Simply raises the speed at which the motor cuts off assistance
- Can usually be toggled on/off from a phone app

---

## Hardware Tools for E-Bike Flashing

| Tool | Purpose | Used for |
|------|---------|---------|
| **ST-Link V2** | SWD programmer | Bafang BBS, TSDZ2, KT controllers (all STM8S-based) |
| **USB cable** | Direct connection | VESC controllers |
| **UART adapter** (CP2102/CH340) | Serial connection | Bafang CAN bus motors, CYC, Lishui |
| **Bafang programming cable** | Connects ST-Link to the motor's SWD header | Bafang BBSHD/BBS02 (some versions have a dedicated connector) |
