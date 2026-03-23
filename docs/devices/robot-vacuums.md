# Robot Vacuums

OSmosis tracks open-source firmware and local control options for robot vacuums. Most supported models use [Valetudo](https://valetudo.cloud/) — a self-hosted local replacement for cloud-dependent vacuum apps — flashed either directly or via [DustBuilder](https://builder.dontvacuum.me/).

**Important:** Robot vacuum firmware is closely tied to hardware revisions and production dates. A model that is supported on one hardware revision may be completely locked on a newer one. Always verify your specific hardware generation before attempting to flash.

All entries on this page are **Research** status. OSmosis does not yet have an automated flash wizard for robot vacuums, but documents the landscape so users can follow community-maintained tools.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Research** | Community tools exist and are documented here. OSmosis does not yet wrap these in a wizard. |
| **Partial** | Limited local control is available (e.g. MQTT only), but no firmware replacement. |
| **Not supported** | Proprietary/locked. No firmware replacement available. Listed for awareness. |

---

## Roborock

Roborock vacuums are among the best-supported targets for Valetudo. Older generations (pre-2021) run on Allwinner/Rockchip SoCs with accessible root via DustBuilder. Newer cloud-only models are progressively locking down.

### S-Series

| Model | Generation | SoC | Flash Method | Valetudo | Status |
|-------|-----------|-----|-------------|---------|--------|
| Roborock S5 | Gen 2 | Allwinner R16 | DustBuilder rooted image via UART or OTA | Yes | Research |
| Roborock S5 Max | Gen 2.5 | Allwinner R16 | DustBuilder | Yes | Research |
| Roborock S6 | Gen 3 | Allwinner R16 | DustBuilder | Yes | Research |
| Roborock S6 Pure | Gen 3 | Allwinner R16 | DustBuilder | Yes | Research |
| Roborock S6 MaxV | Gen 3 | Rockchip | DustBuilder | Yes | Research |
| Roborock S7 | Gen 4 | Rockchip | DustBuilder | Yes | Research |
| Roborock S7 Pro Ultra | Gen 4 | Rockchip | DustBuilder | Yes (limited) | Research |

### Q-Series

| Model | Generation | Flash Method | Valetudo | Status |
|-------|-----------|-------------|---------|--------|
| Roborock Q7 | Gen 4 | DustBuilder | Yes | Research |
| Roborock Q7 Max | Gen 4 | DustBuilder | Yes | Research |
| Roborock Q7+ | Gen 4 | DustBuilder | Yes | Research |

### Key Details

- **DustBuilder** generates a custom rooted firmware image specific to your device's serial number. You download the image, then flash it via the Roborock app's OTA update flow or via UART.
- **UART access:** Open the vacuum's top shell. Locate the UART header on the mainboard (3.3V logic — use a logic-level adapter). This gives a root shell and allows manual flashing without DustBuilder's OTA method.
- **Newer S8/S9 series:** Roborock has progressively hardened newer generations. The S8 Pro Ultra and later use a secure boot chain. Valetudo support is incomplete or absent for these.

---

## Dreame

Dreame vacuums share lineage with Xiaomi and use similar rooting paths. The community-maintained tool is again DustBuilder.

| Model | SoC | Flash Method | Valetudo | Notes | Status |
|-------|-----|-------------|---------|-------|--------|
| Dreame L10 Pro | Allwinner | DustBuilder rooted OTA | Yes | Well-supported generation | Research |
| Dreame L20 Ultra (R2394) | Rockchip | DustBuilder | Yes | **R2394 hardware revision only.** Other L20 Ultra revisions are not supported. | Research |
| Dreame Gen 3 platforms | Rockchip | DustBuilder | Yes (in progress) | Valetudo gen3 support ongoing | Research |

### Key Details

- **R2394 revision lock:** The Dreame L20 Ultra has multiple hardware revisions. Only the R2394 revision is currently rootable and Valetudo-compatible. Check the sticker on the underside of the unit before attempting.
- **DustBuilder for Dreame:** The flow is the same as Roborock — enter serial/model, get a rooted OTA image, push via the Mi Home app or UART.
- **Gen 3 note:** Dreame's third-generation platform (2023+) is partially supported by Valetudo. Stability varies by model. Follow the Valetudo GitHub for current status.

---

## Xiaomi Mi Robot

The original Xiaomi Mi Robot Vacuum (Gen 1) is a classic Valetudo target with a well-documented rooting path.

| Model | SoC | Flash Method | Valetudo | Status |
|-------|-----|-------------|---------|--------|
| Xiaomi Mi Robot Vacuum Gen 1 | Allwinner R16 | DustBuilder / UART / OTA | Yes | Research |

### Key Details

- Gen 1 is one of the most thoroughly documented vacuums in the Valetudo ecosystem.
- **OTA method:** Works on stock firmware versions below a certain patch level. DustBuilder generates a signed-looking image that the stock updater accepts.
- **UART method:** More reliable. UART pads are exposed inside the top shell. Connect at 115200 baud, 3.3V.
- **Gen 2 and later Xiaomi vacuums** (branded as Mijia or sold via Xiaomi's newer lineup) moved to Rockchip SoCs and have varying levels of Valetudo support. Check [robotinfo.dev](https://robotinfo.dev) for your specific model.

---

## Ecovacs

Ecovacs support is partial and primarily the result of security research by [Dennis Giese](https://dontvacuum.me/) (the same researcher behind Valetudo and DustBuilder).

| Model Family | Status | Notes |
|-------------|--------|-------|
| Ecovacs Deebot T8 / T9 | Research (partial) | Root access demonstrated via research. Valetudo port exists but is not stable. |
| Ecovacs Deebot X1 | Research (partial) | Dennis Giese's research documented attack surface. No consumer-ready tool. |
| Older Ecovacs (N-series) | Research | Simpler hardware. Community research ongoing. |

### Key Details

- **Dennis Giese's research** is the primary source for Ecovacs vulnerability and rooting information. See [dontvacuum.me](https://dontvacuum.me/) and his DEF CON / 37C3 presentations for technical details.
- No DustBuilder support for Ecovacs at this time.
- Local MQTT control is possible on some models after root is obtained, but requires manual setup.

---

## iRobot Roomba

iRobot Roomba vacuums have **no firmware replacement** available. However, many models expose a local MQTT/REST API that can be used for home automation without any flashing.

| Model Family | Local Control | Method | Status |
|-------------|--------------|--------|--------|
| Roomba 900 series | Yes | [dorita980](https://github.com/koalazak/dorita980) MQTT | Partial |
| Roomba i-series | Yes | dorita980 / Home Assistant integration | Partial |
| Roomba j-series | Yes (limited) | dorita980 / Home Assistant | Partial |
| Roomba s-series | Yes (limited) | dorita980 | Partial |
| Roomba Combo | Varies | dorita980 | Partial |

### What dorita980 Provides

[dorita980](https://github.com/koalazak/dorita980) is a Node.js library that speaks iRobot's local UDP + MQTT protocol. It allows:

- Starting, stopping, and docking the robot without the iRobot cloud
- Receiving real-time status (cleaning, charging, error state)
- Retrieving map data (on supported models)
- Local-only operation if you block the robot's internet access

### Key Details

- **No firmware replacement:** Roomba firmware is not replaceable with open-source alternatives.
- **Cloud dependency:** By default, Roomba requires an iRobot account and internet connection. dorita980 lets you bypass this for control, but the device still needs initial Wi-Fi setup via the iRobot app.
- **Home Assistant:** The official Home Assistant iRobot integration uses the same local protocol under the hood.

---

## General Notes

### Identifying Your Hardware Revision

Before using DustBuilder or any other tool, identify your exact hardware revision:

1. Check the sticker on the underside of the vacuum for a model number and hardware version string.
2. Cross-reference at [robotinfo.dev](https://robotinfo.dev) — this community database tracks which specific revisions are rootable.
3. For Roborock/Xiaomi, the Mi Home app sometimes shows the hardware version in device info.

### Valetudo vs. Stock App

After flashing Valetudo, the vacuum operates entirely locally:

- Valetudo replaces the cloud firmware component
- A local web UI replaces the manufacturer app
- Works with Home Assistant, Node-RED, and any MQTT client
- No internet connection required during operation

### Safety Note

Robot vacuums contain lithium batteries, spinning brushes, and suction fans. A failed flash can result in a bricked unit. Always use DustBuilder's backup feature to save a copy of your stock firmware before flashing.

---

## Links

| Resource | URL |
|---------|-----|
| Valetudo | https://valetudo.cloud/ |
| DustBuilder | https://builder.dontvacuum.me/ |
| robotinfo.dev (hardware revision database) | https://robotinfo.dev |
| dorita980 (Roomba local API) | https://github.com/koalazak/dorita980 |
| Dennis Giese's research blog | https://dontvacuum.me/ |
| Valetudo GitHub | https://github.com/Hypfer/Valetudo |
