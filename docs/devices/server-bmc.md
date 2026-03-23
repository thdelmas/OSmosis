# Server BMC / IPMI

OSmosis documents open-source BMC (Baseboard Management Controller) firmware for server platforms. BMC firmware provides out-of-band management — remote power control, serial console access, hardware health monitoring, and firmware updates — independent of the main CPU and OS.

The dominant open-source BMC firmware is [OpenBMC](https://github.com/openbmc/openbmc), a Yocto-based Linux distribution maintained by a consortium including Meta, IBM, Google, and Arm.

**Note:** BMC firmware flashing carries high risk. A failed flash on the BMC can render a server completely unrecoverable without physical board-level intervention (e.g. SPI flash reprogramming). Only proceed if you understand the recovery path for your specific hardware.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Supported** | OpenBMC builds available and tested for this platform. Active upstream support. |
| **Experimental** | OpenBMC port exists but may have incomplete functionality or limited testing. |
| **Research** | Community investigation underway. No production-ready build. |
| **Not supported** | Proprietary BMC firmware. No open-source alternative available or planned. |

---

## OpenBMC Platform Overview

OpenBMC targets ASPEED AST2400, AST2500, and AST2600 BMC SoCs — the chips used in the vast majority of server BMCs. Each server platform requires a platform-specific OpenBMC build because BMC firmware must match the exact hardware layout of the server.

| AST SoC | Used In |
|---------|---------|
| AST2400 | Older platforms (pre-2018) |
| AST2500 | Meta Tioga Pass, older IBM POWER9, many X11 Supermicro |
| AST2600 | Current platforms: Meta Grand Teton, IBM POWER10, Google Compute |

---

## Meta / Facebook Platforms

Meta is one of the primary OpenBMC contributors. Their Open Compute Project (OCP) servers are the best-supported OpenBMC targets.

| Platform | BMC SoC | CPU Platform | Status | Notes |
|---------|---------|-------------|--------|-------|
| Tioga Pass | AST2500 | Intel Xeon Scalable | Supported | Classic OCP compute node. Well-tested OpenBMC target. |
| Twin Lakes | AST2500 | Intel | Supported | |
| Wedge 100 | AST2400 | x86 (switch/compute) | Supported | Open Compute network switch |
| Wedge400 | AST2500 | x86 | Supported | |
| Grand Teton | AST2600 | x86 + GPU | Supported | Meta's AI training platform |
| Yosemite v2 | AST2500 | Intel | Supported | Multi-node sled |
| Yosemite v3 | AST2600 | AMD/Intel | Supported | |

### Key Details

- Meta's OCP platforms are designed for OpenBMC from the start. The hardware and BMC target code are co-developed.
- Platform-specific OpenBMC builds are available directly from the [openbmc/openbmc](https://github.com/openbmc/openbmc) repository (`meta-facebook` layer).

---

## IBM POWER

IBM is another primary OpenBMC contributor. Their POWER server BMCs are OpenBMC-based in production firmware.

| Platform | BMC SoC | CPU | Status | Notes |
|---------|---------|-----|--------|-------|
| IBM AC922 (POWER9) | AST2500 | POWER9 | Supported | Original production OpenBMC IBM platform |
| IBM 9009-41A (POWER9) | AST2500 | POWER9 | Supported | |
| IBM 9009-42A (POWER9) | AST2500 | POWER9 | Supported | |
| IBM IC922 (POWER9 + GPU) | AST2500 | POWER9 + V100 | Supported | |
| IBM 9105-22A / 9105-42A (POWER10) | AST2600 | POWER10 | Supported | Scale-out systems |
| IBM 9080-HEX (POWER10) | AST2600 | POWER10 | Supported | High-end enterprise |

### Key Details

- IBM POWER servers ship with OpenBMC as the stock firmware. This is not a community replacement — it is the manufacturer's production firmware.
- Platform code is in the `meta-ibm` and `meta-openpower` layers of the OpenBMC repository.
- IBM's [OpenPOWER](https://openpowerfoundation.org/) initiative opens both the CPU architecture and the BMC firmware stack.

---

## Google Cloud Platforms

Google contributes Titan-secured OpenBMC variants for their custom data center hardware.

| Platform | BMC SoC | Status | Notes |
|---------|---------|--------|-------|
| Google Rainier | AST2600 | Supported | AMD EPYC-based |
| Google Orion | AST2600 | Supported | |
| Google Deluge | AST2600 | Supported | |
| Google Taco | AST2500 | Supported | |

Google's platforms use Titan security chips alongside the AST BMC. Their OpenBMC work is in the `meta-google` layer.

---

## Qualcomm / Arm Development Platforms

| Platform | BMC SoC | Status | Notes |
|---------|---------|--------|-------|
| Qualcomm Centriq (development) | AST2500 | Experimental | Development reference only |
| Arm Neoverse N1 SDP | AST2500 | Experimental | System development platform |

---

## ASPEED Evaluation Boards

ASPEED's own evaluation boards (AST2500 EVB, AST2600 EVB) are supported OpenBMC targets and are commonly used for BMC firmware development and testing.

| Board | BMC SoC | Status |
|-------|---------|--------|
| AST2500 EVB | AST2500 | Supported |
| AST2600 EVB | AST2600 | Supported |
| ASPEED AST2600 A3 EVB | AST2600 | Supported |

---

## Supermicro

Supermicro uses ASPEED AST BMC chips across their product line, making OpenBMC theoretically possible. In practice, Supermicro's hardware layout (fan controllers, power sequencing ICs, FRU data) is highly board-specific and not fully supported by community OpenBMC builds.

| Platform | BMC SoC | Status | Notes |
|---------|---------|--------|-------|
| Supermicro X11 (select boards) | AST2500 | Experimental | Some X11 boards have community OpenBMC work. Not production-ready. |
| Supermicro X12 / H12 | AST2600 | Research | No community OpenBMC build. |
| Supermicro X13 / H13 | AST2600 | Research | Current generation. No community build. |

### Key Details

- Supermicro's IPMI firmware (IPMI v2.0 / Redfish) is proprietary and feature-complete. Most users do not have a reason to replace it.
- The primary motivation for OpenBMC on Supermicro would be security auditing or locked IPMI features, not added functionality.
- Supermicro's BMC has been the subject of multiple CVEs (including the 2018 Supermicro supply chain research). If security is the concern, OpenBMC provides a fully auditable alternative.

---

## Dell iDRAC / HPE iLO

Dell's iDRAC (Integrated Dell Remote Access Controller) and HPE's iLO (Integrated Lights-Out) are proprietary BMC implementations. They are not supported by OpenBMC and have no open-source alternatives.

| System | BMC | Firmware | Status |
|--------|-----|---------|--------|
| Dell PowerEdge (all generations) | iDRAC 7/8/9/10 | Proprietary (Dell) | Not supported |
| HPE ProLiant (all generations) | iLO 4/5/6 | Proprietary (HPE) | Not supported |
| Lenovo ThinkSystem | XCC (IPMI) | Proprietary (Lenovo) | Not supported |
| Cisco UCS | CIMC | Proprietary (Cisco) | Not supported |

### Key Details

- iDRAC and iLO are mature, feature-rich BMC implementations with Redfish, virtual media, remote console, and strong enterprise tooling.
- There is no community interest or active work to replace these with OpenBMC.
- They are listed here so users understand why OSmosis cannot assist with these platforms.

---

## OpenBMC Features (When Supported)

When OpenBMC is running on a supported platform, it provides:

| Feature | Description |
|---------|------------|
| **Redfish API** | REST API for remote management (power, sensors, firmware update, event logs) |
| **IPMI** | Legacy IPMI 2.0 over LAN for compatibility with existing tools |
| **KVM / Serial console** | Remote console access via the web UI or IPMI |
| **Virtual media** | Mount ISO images remotely for OS installation |
| **Firmware update** | Update BMC, BIOS, and CPLD firmware via Redfish |
| **Hardware sensors** | Temperature, fan speed, voltage, power consumption monitoring |
| **Event log** | SEL (System Event Log) via IPMI and Redfish |
| **Secure boot** | Some platforms support measured boot and attestation |

---

## Flashing OpenBMC

The general procedure for flashing OpenBMC varies by platform but typically involves one of:

| Method | Used When |
|--------|----------|
| Redfish `UpdateService` API | Current BMC is functional and network-accessible |
| IPMI `hpm update` or `ipmitool` | Current BMC is functional, legacy access |
| U-Boot serial console | BMC boots but network access is broken |
| SPI flash programmer (CH341A or equivalent) | BMC is completely bricked — physical recovery |

**Always verify the platform target** before building or flashing OpenBMC. Flashing a mismatched platform image will brick the BMC.

---

## Links

| Resource | URL |
|---------|-----|
| OpenBMC GitHub | https://github.com/openbmc/openbmc |
| OpenBMC documentation | https://github.com/openbmc/docs |
| OpenBMC project website | https://www.openbmc.org/ |
| OpenPOWER Foundation | https://openpowerfoundation.org/ |
| Open Compute Project (OCP) | https://www.opencompute.org/ |
| ASPEED Technology | https://www.aspeedtech.com/ |
