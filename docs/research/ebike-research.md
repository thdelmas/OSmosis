# E-Bike Controller Flashing — Research

Research into electric bike motor controller firmware flashing, covering the
community landscape, open-source projects, hardware requirements, and risks.

---

## Overview

E-bike controller flashing is a well-established practice in the DIY e-bike
community. Riders flash their motor controllers to unlock speed limits, increase
power output, customize pedal assist behavior, and add features like throttle
control. The ecosystem is comparable to the scooter CFW scene but targets
different hardware (mid-drive and hub motor controllers).

Two main approaches exist:

1. **Parameter tuning** — adjusting settings (speed, current, PAS levels) via
   the LCD display or companion software within the stock firmware.
2. **Full firmware flashing** — replacing the stock firmware entirely with
   custom or open-source firmware for deep control over motor behavior.

---

## Major Open-Source Firmware Projects

### bbs-fw (Bafang BBSHD / BBS02)

- **Repository:** https://github.com/danielnilsson9/bbs-fw
- **Target:** Bafang BBSHD and BBS02 mid-drive motor controllers
- **Description:** Replaces the original Bafang firmware. Implements nearly all
  original functionality plus additional features (configurable assist levels,
  throttle mapping, current limits, speed limits, street/offroad modes).
- **Chip:** STM8S (same family as many scooter controllers)
- **Programmer:** ST-Link V2
- **Community:** Active GitHub issues and wiki with flashing instructions.

### bbshd-fw

- **Repository:** https://github.com/fpdragon/bbshd-fw
- **Target:** Bafang BBSHD controllers specifically
- **Description:** Alternative custom firmware focused on BBSHD tuning.

### TSDZ2 Open Source Firmware (OSF)

- **Website:** https://opensourceebikefirmware.bitbucket.io/
- **Target:** Tongsheng TSDZ2 mid-drive motor controllers
- **Chip:** STM8S (flashed via ST-Link V2)
- **Description:** Community-developed firmware with torque sensor support,
  configurable assist levels, field weakening, and advanced motor control.
- **Ecosystem:** Compatible displays (850C, 860C) with dedicated firmware.
  Complete upgrade kits available (controller + display + harness).

### Stancecoke / BMSBattery_S Controllers Firmware

- **Repository:** https://github.com/stancecoke/BMSBattery_S_controllers_firmware
- **Target:** Kunteng (KT) sine wave controllers, BMS Battery S controllers
- **Chip:** STM8 microcontroller
- **Description:** Change virtually any parameter: throttle response, PAS
  sensitivity, torque sensor curves, brake behavior, display protocol.
  Enables true sine wave control for smoother motor operation.

### VESC (Vedder Electronic Speed Controller)

- **Target:** Custom high-performance builds
- **Description:** Open-source motor controller hardware and firmware. Supports
  FOC (Field Oriented Control) for efficient, quiet motor driving. Popular
  in DIY e-bike and e-skateboard builds. Full configuration tool (VESC Tool).
- **Note:** VESC is both hardware and firmware — users build or buy VESC-based
  controllers rather than flashing existing OEM controllers.

---

## Hardware Requirements

| Item | Purpose | Approx. Cost |
|------|---------|-------------|
| ST-Link V2 programmer | Flashing STM8-based controllers (Bafang, TSDZ2, KT) | ~$3-10 |
| USB-to-serial adapter | UART-based flashing for some controllers | ~$5 |
| Soldering iron | Accessing programming headers on some controllers | — |
| VESC Tool (software) | Configuring VESC-based controllers | Free |

The ST-Link V2 is the same programmer already used for scooter ST-Link flashing
in Osmosis, which means existing infrastructure can be reused.

---

## Configurable Parameters (typical)

- Speed limits (per assist mode: eco / touring / sport / turbo)
- Motor current limits (max amps to the motor)
- Battery current limits (max draw from battery)
- Pedal Assist Sensor (PAS) levels and multipliers
- Torque sensor curves and sensitivity
- Throttle mapping and response curves
- KERS / regenerative braking intensity
- Field weakening (higher speed at cost of efficiency)
- Low-voltage cutoff thresholds
- Street mode / offroad mode toggle
- Display protocol selection (KT-LCD3, 850C, 860C, etc.)

---

## Risks and Considerations

- **Bricking:** Power loss during a firmware flash can permanently brick the
  controller, requiring replacement (~$30-150 depending on the unit).
- **Warranty void:** Flashing custom firmware voids the manufacturer warranty.
- **Legal compliance:** Many jurisdictions limit e-bike motor power and speed
  (e.g., EU: 250W / 25 km/h, US: varies by class). Unlocking limits may
  reclassify the bike as a moped or motorcycle, requiring registration and
  insurance.
- **Motor/battery damage:** Incorrect current limits can overheat the motor or
  overdraw the battery, causing permanent damage or fire risk.
- **Compatibility:** Not all controller hardware revisions are flashable.
  Some newer Bafang units have locked bootloaders.

---

## Relevance to Osmosis

The e-bike flashing ecosystem shares significant overlap with Osmosis's existing
scooter support:

| Aspect | Scooter (existing) | E-Bike (new) |
|--------|-------------------|--------------|
| Primary chip | STM32 / AT32 | STM8S (same ST family) |
| Programmer | ST-Link V2 | ST-Link V2 (identical) |
| Wireless flash | BLE (Ninebot protocol) | Not common (wired only) |
| CFW builders | ScooterHacking | bbs-fw config tool |
| Parameter tuning | Register read/write over BLE | Display menus / UART |
| Community size | Large (ScooterHacking, Endless Sphere) | Large (Endless Sphere, Pedelecs, EBR) |

Key takeaway: **ST-Link flashing infrastructure is directly reusable.** The main
new work is controller identification, firmware project integration, and a
parameter configuration UI.

---

## Community and Resources

- [Endless Sphere Forum](https://endless-sphere.com/) — largest DIY e-bike community
- [Pedelecs Forum](https://www.pedelecs.co.uk/forum/) — UK-focused e-bike community
- [bbs-fw Wiki](https://github.com/danielnilsson9/bbs-fw/wiki) — flashing instructions for Bafang
- [TSDZ2 OSF Wiki](https://opensourceebikefirmware.bitbucket.io/) — TSDZ2 firmware docs
- [Hackaday: An Open Source Ebike](https://hackaday.com/2020/02/23/an-open-source-ebike/)
- [Letrigo: DIY Guide to Flashing Controllers](https://letrigo.com/blogs/knowledge/flashing-kt-or-sine-wave-ebike-controller)
- [House Dillon: Flash e-bike Series](https://housedillon.com/blog/flash-part-seven/)
