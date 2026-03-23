# Desktop & Laptop Firmware

OSmosis supports flashing open-source firmware (Libreboot, Coreboot, and open EC firmware) on a range of desktop and laptop hardware. This page covers every supported platform, its flash method, and current support status.

**Important:** Reflashing system firmware carries a risk of bricking your hardware if the process is interrupted or an incorrect image is used. Always read the upstream documentation for your specific board revision before proceeding, and back up your current firmware image first.

---

## Overview of Support Levels

| Status | Meaning |
|--------|---------|
| **Supported** | Tested, stable, and integrated into the OSmosis wizard |
| **Planned** | Hardware identified and tooling exists; OSmosis wizard flow in progress |
| **Research** | Community interest exists but no reliable, generalizable flash path yet |

---

## ThinkPad (Libreboot)

[Libreboot](https://libreboot.org/) is a fully free (no binary blobs) coreboot distribution. Only older ThinkPads are supported because newer Intel hardware requires proprietary blobs for memory initialization.

| Device | Flash Method | Libreboot Status | Notes |
|--------|-------------|-----------------|-------|
| ThinkPad X60 | flashrom internal or SPI clip | Fully free, no blobs | First fully-free laptop target |
| ThinkPad T60 | flashrom internal or SPI clip | Fully free, no blobs | ATI GPU variant only (Intel GPU T60 also works) |
| ThinkPad X200 | flashrom (SPI clip) or CH341A | Libreboot + me_cleaner | Intel ME neutralized via [me_cleaner](https://github.com/corna/me_cleaner) |
| ThinkPad T400 | flashrom (SPI clip) or CH341A | Libreboot + me_cleaner | |
| ThinkPad T500 | flashrom (SPI clip) or CH341A | Libreboot + me_cleaner | |

### Flash Methods

| Method | Description |
|--------|-------------|
| **flashrom internal** | Software-only flash from a running Linux system. Requires the `ich_spi` or `lpc_ich` kernel module and may need an older kernel on some boards. |
| **SPI clip (Pomona 5250)** | Hardware clip attaches directly to the SOIC-8 flash chip. External programmer (e.g. CH341A) sends the image without needing to boot the machine. Required for bricked boards and for initial flash when the vendor BIOS locks internal access. |
| **CH341A** | Cheap USB SPI programmer (~$5). Works with flashrom. Connect via Pomona SPI clip or probe directly to chip pins. |

### Key Details

- **X60/T60:** The SPI flash chip is large enough to be reflashed from within a running system using `flashrom -p internal`. No hardware programmer needed for a first-time flash.
- **X200/T400/T500:** The ME region must be cleaned with me_cleaner before writing. Libreboot's build system handles this automatically.
- **Libreboot project:** [libreboot.org](https://libreboot.org/)

---

## ThinkPad (Coreboot)

[Coreboot](https://www.coreboot.org/) with proprietary binary blobs (for memory initialization / MRC) supports a wider range of ThinkPads than Libreboot. Payload options include SeaBIOS (for legacy/CSM boot) and GRUB (for direct Linux boot without a bootloader on disk).

| Device | Flash Method | Payload Options | OSmosis Support |
|--------|-------------|----------------|----------------|
| ThinkPad X230 | SPI clip or 1vyrain | SeaBIOS, GRUB | Supported |
| ThinkPad T430 | SPI clip or 1vyrain | SeaBIOS, GRUB | Supported |
| ThinkPad T530 | SPI clip | SeaBIOS, GRUB | Supported |
| ThinkPad W530 | SPI clip | SeaBIOS, GRUB | Supported |
| ThinkPad T440p | SPI clip | SeaBIOS, GRUB | Planned |
| ThinkPad T450s | SPI clip | SeaBIOS, GRUB | Planned |
| ThinkPad X250 | SPI clip | SeaBIOS, GRUB | Planned |

### Flash Methods

| Method | Devices | Description |
|--------|---------|-------------|
| **SPI clip + CH341A** | All | Universal hardware method. Requires opening the machine and clipping to the 8-pin SOIC flash chip. |
| **[1vyrain](https://github.com/n4ru/1vyrain)** | X230, T430 | Software-only exploit using a UEFI vulnerability present in certain vendor BIOS versions. No hardware required. Patches the vendor BIOS to allow coreboot installation without a programmer. |

### Key Details

- **1vyrain:** Works only on X230 and T430 at specific BIOS versions. The tool auto-detects eligibility. It is the easiest path for those models — no soldering or hardware programmer required.
- **me_cleaner:** Recommended for all Sandy Bridge/Ivy Bridge ThinkPads (X230, T430, T530, W530). Coreboot's build system can invoke me_cleaner during image creation.
- **Binary blobs:** Unlike Libreboot, these builds include Intel MRC (memory reference code) blobs. The resulting firmware is open-source but not fully free.
- **Coreboot project:** [coreboot.org](https://www.coreboot.org/)

---

## Chromebooks (MrChromebox)

[MrChromebox](https://mrchromebox.tech/) provides full UEFI replacement firmware (based on coreboot + Tianocore EDK2) for most x86 Chromebooks from 2014 onward, enabling installation of any standard OS.

| Generation | Years | Full ROM UEFI | WP Method | OSmosis Support |
|-----------|-------|--------------|-----------|----------------|
| Bay Trail | 2014–2015 | Yes | Write-protect screw | Planned |
| Broadwell | 2015–2016 | Yes | Write-protect screw | Planned |
| Skylake | 2016 | Yes | Write-protect screw | Planned |
| Kaby Lake | 2017 | Yes | Write-protect screw | Planned |
| Apollo Lake | 2016–2018 | Yes | Write-protect screw | Planned |
| Gemini Lake | 2018–2019 | Yes | Write-protect screw | Planned |
| Whiskey Lake | 2018–2019 | Yes | Write-protect screw | Planned |
| Comet Lake | 2020 | Yes | CR50 console | Planned |
| Tiger Lake | 2021 | Yes | CR50 console | Planned |
| Alder Lake | 2022 | Yes | CR50 console | Planned |
| Jasper Lake | 2021–2022 | Yes | CR50 console | Planned |
| ARM (all) | 2012–present | No full UEFI ROM | — | Research |

### Write-Protect Removal

Chromebook firmware is protected by a hardware write-protect mechanism. It must be disabled before the full ROM can be flashed.

| Method | Models |
|--------|--------|
| **Write-protect screw removal** | Most pre-2019 models. A single screw on the motherboard bridges the WP circuit. Remove it with the battery disconnected. |
| **CR50/GSC console** | 2019+ models with a Titan/CR50 security chip. Boot to recovery mode, open the CR50 serial console via USB, and issue `wp disable` commands. |

### Flash Procedure

1. Remove write protection (screw or CR50).
2. Boot ChromeOS, open a crosh terminal (`Ctrl+Alt+T`, then `shell`).
3. Run the MrChromebox script:
   ```
   curl -LO mrchromebox.tech/firmware-util.sh && sudo bash firmware-util.sh
   ```
4. Select **Install/Update UEFI (Full ROM) Firmware**.
5. The script downloads the correct image for your board and flashes it via `flashrom`.

### Key Details

- **ARM Chromebooks:** MrChromebox does not produce full UEFI ROMs for ARM boards. U-Boot and other ARM bootloaders are being explored by the community, but there is no reliable, generalizable path. Listed as Research only.
- **Recovery:** Keep a USB recovery drive. If the full ROM flash fails, recovery mode can restore ChromeOS.
- **MrChromebox project:** [mrchromebox.tech](https://mrchromebox.tech/)

---

## System76

[System76](https://system76.com/) ships open-source embedded controller (EC) firmware on all current products. Firmware updates are delivered through `system76-firmware-cli` (System76's own updater) and through [fwupd](https://fwupd.org/) on supported distributions.

| Device Family | Models | EC Firmware | Flash Tool | OSmosis Support |
|--------------|--------|------------|-----------|----------------|
| Laptops | Galago Pro, Lemur Pro, Oryx Pro, Darter Pro | Open-source ([system76-ec](https://github.com/system76/ec)) | `system76-firmware-cli` / fwupd | Supported |
| Desktops | Thelio, Thelio Major, Thelio Mira, Thelio Mega | Open-source EC | `system76-firmware-cli` / fwupd | Supported |

### OS Compatibility

| OS | Notes |
|----|-------|
| **Pop!_OS** | System76's own Ubuntu-based distro. Full firmware update support out of the box. |
| **Ubuntu / Debian** | Install `system76-firmware` package from the System76 PPA. |
| **Other Linux** | Use fwupd where supported; otherwise use `system76-firmware-cli` from source. |

### Flash Procedure

```
# Install the CLI tool (Pop!_OS / Ubuntu with System76 PPA)
sudo apt install system76-firmware

# Schedule a firmware update (applies on next reboot)
system76-firmware-cli schedule

# Reboot — firmware flashes automatically during POST
sudo systemctl reboot
```

### Key Details

- **EC firmware is fully open-source:** Source at [github.com/system76/ec](https://github.com/system76/ec), based on the Chromium EC codebase.
- **UEFI/BIOS:** System76 uses coreboot on some newer models (Lemur Pro, Galago Pro). Check [system76.com/coreboot](https://system76.com/coreboot) for the current list.
- **fwupd:** Updates are published to the Linux Vendor Firmware Service (LVFS). On supported distros, `fwupdmgr update` is all that is needed.

---

## Framework Laptop

[Framework](https://frame.work/) publishes open-source EC firmware for all laptop generations, based on a fork of Chromium EC. The UEFI/BIOS remains a proprietary AMI implementation.

| Device | EC Firmware | Flash Method | UEFI/BIOS | OSmosis Support |
|--------|------------|-------------|----------|----------------|
| Framework Laptop 13 (Intel 11th–13th gen) | Open-source ([framework-ec](https://github.com/FrameworkComputer/EmbeddedController)) | `flash_ec` via USB-C debug port | Proprietary AMI | Planned |
| Framework Laptop 13 (AMD Ryzen 7040) | Open-source | `flash_ec` via USB-C debug port | Proprietary AMI | Planned |
| Framework Laptop 16 | Open-source | `flash_ec` via USB-C debug port | Proprietary AMI | Planned |

### EC Flash Procedure

The EC is flashed using the `flash_ec` script from the Framework EC repository:

```
git clone https://github.com/FrameworkComputer/EmbeddedController
cd EmbeddedController
sudo ./util/flash_ec --board=hx20   # Framework 13 Intel
```

- Connect a USB-C cable to the **debug port** (left rear USB-C on Framework 13).
- The laptop must be powered on and running Linux.
- The script halts the EC, writes the new image over USB, and reboots the EC.

### Key Details

- **EC firmware:** Chromium EC fork. Source at [github.com/FrameworkComputer/EmbeddedController](https://github.com/FrameworkComputer/EmbeddedController).
- **UEFI/BIOS:** AMI firmware. Framework publishes BIOS update packages via their Drivers & Downloads page. No open-source BIOS is available for Framework hardware at this time.
- **fwupd:** Framework BIOS updates are available through LVFS on recent generations. `fwupdmgr update` will apply them.
- **Expansion cards:** Framework's modular USB-C expansion cards do not require firmware updates.

---

## PC Motherboards

Several desktop motherboards have well-established coreboot ports, making them suitable for fully open-source desktop builds.

| Board | Chipset | Coreboot Status | Flash Method | OSmosis Support |
|-------|---------|----------------|-------------|----------------|
| Supermicro X9SRL-F | Intel C602 | Well-supported | flashrom internal or SPI clip | Supported |
| Supermicro X10SLL-F | Intel C222 | Well-supported | flashrom internal or SPI clip | Supported |
| ASUS KGPE-D16 | AMD SR5670 / SP5100 | Well-supported | flashrom internal or SPI clip | Supported |
| ASRock E350M1 | AMD A50M (Fusion) | Supported | flashrom internal | Supported |
| Intel NUC (Haswell/Broadwell) | Intel H81/H87 | Partial, research | flashrom (if WP disabled) | Research |

### Key Details

- **Supermicro X9/X10:** Server-grade boards with IPMI. Coreboot support is mature. flashrom can often write internally if the BIOS write-protect is cleared via jumper.
- **ASUS KGPE-D16:** Dual Opteron (G34) workstation board. One of the most popular coreboot desktop targets. Libreboot also supports this board.
- **ASRock E350M1:** AMD Brazos/Fusion APU mini-ITX board. Inexpensive and well-tested with coreboot.
- **Intel NUC:** Community coreboot efforts exist for Haswell/Broadwell NUCs but require disabling the SPI write-protect via hardware and the port is not fully maintained. Listed as Research.

---

## Network & Firewall Appliances

Dedicated firewall appliances are popular coreboot targets because they are always-on and benefit most from firmware-level security. Both families below ship coreboot either officially or via a well-maintained community port.

| Device | Coreboot Source | Flash Tool | OSmosis Support |
|--------|----------------|-----------|----------------|
| Protectli Vault (FW2/FW4/FW6/VP series) | Official (Protectli) | Flashli script + flashrom | Supported |
| PC Engines APU2 | Community ([pcengines/coreboot](https://github.com/pcengines/coreboot)) | flashrom internal | Supported |
| PC Engines APU3 | Community | flashrom internal | Supported |
| PC Engines APU4 | Community | flashrom internal | Supported |

### Protectli Vault

Protectli ships coreboot as the official firmware for all Vault models. Updates are distributed as binary images and flashed using their Flashli utility (a thin wrapper around flashrom).

```
# Download and run Flashli (Linux)
wget https://kb.protectli.com/files/flashli.sh
sudo bash flashli.sh -c <firmware-image.rom>
```

- Source for Protectli coreboot builds: [github.com/protectli-root/protectli-firmware](https://github.com/protectli-root/protectli-firmware)

### PC Engines APU2/APU3/APU4

The PC Engines community maintains an active coreboot fork with regular releases. The SPI flash is accessible from the running system — no hardware programmer required.

```
# Flash from a running system (e.g. pfSense, OPNsense, Alpine Linux)
flashrom -p internal -w apu2_<version>.rom
```

- Community coreboot: [github.com/pcengines/coreboot](https://github.com/pcengines/coreboot)
- Release images: [pcengines.github.io](https://pcengines.github.io/)

---

## Community Tools

| Tool | Purpose | Source / Link |
|------|---------|--------------|
| **flashrom** | Universal SPI/LPC flash programmer. Reads, writes, and verifies firmware chips. Works with dozens of programmer hardware and internal bus interfaces. | [flashrom.org](https://www.flashrom.org/) / [github.com/flashrom/flashrom](https://github.com/flashrom/flashrom) |
| **me_cleaner** | Neutralizes the Intel Management Engine (ME) by stripping non-essential partitions and setting the HAP/AltMeDisable bit. Reduces ME attack surface significantly. | [github.com/corna/me_cleaner](https://github.com/corna/me_cleaner) |
| **CH341A** | Inexpensive (~$5) USB SPI programmer. Widely available. Works with flashrom for external chip programming. Requires a Pomona 5250 SOIC-8 clip for in-circuit use. | AliExpress, Amazon |
| **MrChromebox firmware-util.sh** | Interactive script that detects your Chromebook board and flashes the correct coreboot/UEFI full ROM image. | [mrchromebox.tech](https://mrchromebox.tech/) |
| **1vyrain** | Software-only BIOS unlock and coreboot installer for ThinkPad X230 and T430. Exploits a UEFI vulnerability to bypass SPI write-protect without hardware. | [github.com/n4ru/1vyrain](https://github.com/n4ru/1vyrain) |
| **system76-firmware-cli** | CLI tool for scheduling and applying System76 firmware (EC + coreboot) updates. Ships with Pop!_OS; available via PPA on Ubuntu. | [github.com/system76/firmware-update](https://github.com/system76/firmware-update) |
| **fwupd** | Linux Vendor Firmware Service client. Applies firmware updates from LVFS for System76, Framework, Protectli, and many others. | [fwupd.org](https://fwupd.org/) / [github.com/fwupd/fwupd](https://github.com/fwupd/fwupd) |
| **flash_ec** | Framework/Chromium EC flashing script. Communicates with the EC over USB-C debug port or internal interface. | [github.com/FrameworkComputer/EmbeddedController](https://github.com/FrameworkComputer/EmbeddedController) |

---

## Hardware Programmers

| Hardware | Purpose | Notes |
|----------|---------|-------|
| **CH341A USB programmer** | External SPI flash programmer | Cheap and widely available. The 3.3 V output on stock units is often out-of-spec (closer to 5 V); use a voltage regulator mod or a pre-modded unit to avoid damaging flash chips. |
| **Pomona 5250 SOIC-8 clip** | In-circuit clip for 8-pin SPI flash chips | Connects to CH341A or other programmers without desoldering the chip. |
| **Raspberry Pi (any model)** | SPI programmer via GPIO | flashrom supports the `linux_spi` programmer. Use with a jumper wire harness to the chip or SPI clip. More reliable 3.3 V than a stock CH341A. |
| **Bus Pirate** | Multi-protocol programmer (SPI, I2C, JTAG, UART) | Slower than CH341A but more versatile for debugging. |

---

## General Notes

### Before Flashing

1. **Identify your exact board revision.** Coreboot and Libreboot images are board-specific. Flashing the wrong image will brick the device.
2. **Read the upstream wiki for your board.** [libreboot.org/docs/](https://libreboot.org/docs/) and [coreboot.org/Board:](https://coreboot.org/status/board-status.html) are the authoritative references.
3. **Back up your current firmware.** Use `flashrom -p <programmer> -r backup.rom` before writing anything. Keep this backup in a safe place — it contains board-specific data (MAC addresses, serial numbers, ME configuration) that cannot be recovered otherwise.
4. **Verify the image before writing.** Run `flashrom -p <programmer> -v <image.rom>` to verify a written image matches what you intended.
5. **Do not interrupt the flash.** A power loss or crash mid-write leaves a partially written chip. On boards without a fallback ROM, this is a hard brick requiring external reprogramming.
6. **Check write-protect.** Many boards have a hardware write-protect jumper, screw, or GPIO that must be cleared before flashrom can write. Check your board's datasheet or coreboot wiki page.

### Recovery

If a board is bricked after a bad flash, it can almost always be recovered by re-flashing externally with a CH341A or Raspberry Pi and a Pomona SPI clip — provided the flash chip is still physically intact and accessible.
