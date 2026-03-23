# Calculators

OSmosis documents jailbreaks, third-party OS replacements, and add-in platforms for graphing calculators. This is a research-heavy category where OS version gating is the primary challenge — manufacturers frequently push firmware updates that patch jailbreak entry points.

All entries on this page are **Research** status. OSmosis documents the landscape and tools; automated wizard support is not yet available.

---

## Support Levels

| Level | Meaning |
|-------|---------|
| **Research** | Community tools exist and are documented. OSmosis does not yet provide a wizard. |
| **Not supported** | No OS replacement or jailbreak available for the current firmware. Add-ins or OS version gating may apply. |

---

## Texas Instruments TI-84 Plus CE

The TI-84 Plus CE is the most common US high school graphing calculator. It runs TI's proprietary OS on an eZ80 processor. Jailbreaking requires downgrading to a vulnerable OS version.

### arTIfiCE Jailbreak

| Tool | Version Required | Method | Status |
|------|----------------|--------|--------|
| [arTIfiCE v2](https://yvantt.github.io/arTIfiCE/) | OS 5.5.x and below | USB cable + TI Connect CE | Research |

arTIfiCE is not a firmware replacement — it is a jailbreak that exploits a vulnerability in the TI-84 Plus CE's OS to run unsigned C programs (ASM/C apps). Once applied:

- **Cesium** (open-source shell/launcher) can be installed, giving a file manager, program launcher, and calculator-like interface on top of the jailbreak
- Homebrew games, tools, and custom programs written in C or assembly can run

### OS Version Gating

| OS Version | arTIfiCE Status |
|-----------|----------------|
| 5.3.x and below | Supported (older exploit path) |
| 5.4.x – 5.5.x | Supported (arTIfiCE v2) |
| 5.6.x and above | **Patched.** arTIfiCE v2 does not work. |
| 5.7.0 (current as of 2024) | **Not supported.** |

**Critical:** If your TI-84 Plus CE is running OS 5.6.0 or newer, there is currently no jailbreak available. Do not update if you are on a jailbreakable version.

### Downgrading

Downgrading the OS is possible on most TI-84 Plus CE hardware revisions using TI Connect CE. TI's signing does not prevent installing older official OS versions. However, some newer hardware revisions ("M" suffix and newer) have patched the bootloader and cannot downgrade below OS 5.6.

### Cesium

[Cesium](https://github.com/mateoconlechuga/cesium) is the standard jailbreak shell for TI-84 Plus CE. It adds:

- File manager for programs and apps
- Variable viewer
- Clock display
- Theming support
- Custom program launching

---

## Texas Instruments TI-Nspire CX / CX II

The TI-Nspire family runs on ARM processors and supports a more capable jailbreak environment, including the ability to boot Linux.

### Ndless Jailbreak

| Device | Tool | Method | Status |
|--------|------|--------|--------|
| TI-Nspire CX (original) | [Ndless](https://ndless.me/) | USB transfer via Nspire Student Software or nspire-tools | Research |
| TI-Nspire CX CAS | Ndless | USB transfer | Research |
| TI-Nspire CX II | Ndless | USB transfer | Research |
| TI-Nspire CX II CAS | Ndless | USB transfer | Research |
| TI-Nspire CX II-T | Ndless | USB transfer | Research |

[Ndless](https://ndless.me/) is the primary TI-Nspire jailbreak. It unlocks native ARM code execution, enabling:

- Homebrew applications and games
- **nDoom, nQuake, and other ports**
- **Linux boot:** [TI-Nspire Linux](https://github.com/tangrs/nspire-linux) allows booting a minimal Linux userspace from Ndless
- Lua script enhancements beyond TI's sandboxed Lua
- GBA emulators, file managers, and productivity tools

### OS Version Gating

| OS Version | Ndless Status |
|-----------|--------------|
| 3.1 – 4.5.x | Full Ndless support |
| 5.0.x – 5.2.x | Ndless supported (CX original) |
| 5.3.x (CX II current) | Check ndless.me for current compatibility; may require specific subversion |
| Latest CX II firmware | Verify at ndless.me before updating |

**Do not update** your TI-Nspire OS without checking Ndless compatibility first.

### Linux on TI-Nspire

Booting Linux on the TI-Nspire CX is a community project:

- Requires Ndless already installed
- Boots a minimal ARM Linux userspace
- Not a full desktop — useful for demos and development, not daily use
- The CX II has more RAM (64MB) and a faster CPU than the original CX, making it a better Linux target

---

## NumWorks N0110 / N0115

NumWorks is a French graphing calculator designed from the ground up to be hackable. It publishes full hardware schematics and firmware source code.

| Device | Chip | Official OS | Alt Firmware | Flash Method |
|--------|------|------------|-------------|-------------|
| NumWorks N0110 | STM32F730 | [Epsilon](https://github.com/numworks/epsilon) | [Omega](https://getomega.dev/), [Upsilon](https://getupsilon.web.app/) | WebDFU (browser-based) |
| NumWorks N0115 | STM32F730 | Epsilon | Omega / Upsilon | WebDFU |

### Omega and Upsilon

[Omega](https://getomega.dev/) is a community fork of NumWorks's official Epsilon OS. It restores features that NumWorks removed in newer Epsilon versions (exam mode lock, Python modules) and adds new ones.

[Upsilon](https://getupsilon.web.app/) is a fork of Omega with additional features, including:

- Python module re-additions (scipy, matplotlib stubs)
- KhiCAS (Xcas computer algebra system) integration
- Additional apps and exam mode bypasses
- Active development community

### WebDFU Flash Method

NumWorks uses a browser-based DFU tool at [my.numworks.com](https://my.numworks.com/) for official firmware. Community tools (Omega, Upsilon) provide their own WebDFU pages:

1. Connect the calculator to a computer via USB.
2. Press RESET + 6 to enter DFU mode (calculator shows a DFU screen).
3. Open the project's WebDFU page in Chrome or Edge (WebUSB required).
4. Follow the on-screen steps to flash.

No desktop software is required.

### Firmware Version Gating (N0115)

NumWorks introduced a bootloader lock in Epsilon firmware 16.x+ for the N0115 hardware revision. On affected units:

- Firmware 16.0.0 and above **locks out third-party firmware permanently** on N0115
- The lock is enforced in the bootloader and cannot be reversed
- N0110 units on older firmware can still install Omega/Upsilon

**Do not update** a NumWorks N0115 past firmware 15.x if you intend to install Omega or Upsilon.

---

## Casio fx-CG50 (Prizm)

The Casio fx-CG50 supports **add-ins** — small C programs compiled against Casio's official SDK and distributed as `.g3a` files. There is no full OS replacement.

| Device | Add-in Support | OS Replacement | Status |
|--------|--------------|---------------|--------|
| Casio fx-CG50 | Yes (official SDK) | No | Research (add-ins only) |
| Casio fx-CG20 (Prizm) | Yes | No | Research (add-ins only) |

### Add-In Ecosystem

- Casio provides an official add-in SDK (for Windows) for developing `.g3a` applications.
- The community has reverse-engineered additional syscalls to access more hardware functionality.
- Notable add-ins: KhiCAS (CAS system), Graph3DP (3D graphing), PeanutGB (Game Boy emulator).
- Add-ins are transferred via USB mass storage — no special tool needed.

---

## HP Prime

The HP Prime is a color touchscreen graphing calculator running a proprietary OS.

| Device | Tool | Status | Notes |
|--------|------|--------|-------|
| HP Prime G1 | HP Connectivity Kit (official) | Research | Official tool for OS updates and program transfer |
| HP Prime G2 | HP Connectivity Kit (official) | Research | |
| HP Prime G2 | Rip'Em (experimental) | Research | Experimental jailbreak. Limited functionality. Community project. |

The HP Connectivity Kit is the official Windows/macOS tool for transferring programs, notes, and apps to the HP Prime. It also handles firmware updates.

**Rip'Em** is a community-developed experimental jailbreak that has shown limited success on certain G2 firmware versions. It is not production-ready.

---

## Casio fx-9860GII

Like the fx-CG50, the Casio fx-9860GII supports add-ins via Casio's official SDK. No OS replacement exists.

| Device | Add-in Support | OS Replacement | Status |
|--------|--------------|---------------|--------|
| Casio fx-9860GII | Yes | No | Research (add-ins only) |
| Casio fx-9860GII SD | Yes | No | Research (add-ins only) |

Add-ins for the fx-9860GII are `.g1a` files, transferred via Casio's official FA-124 software or USB mass storage.

---

## General Notes

### Before Updating Calculator Firmware

Calculator jailbreaks are version-specific. If you are on a jailbreakable firmware version:

1. **Do not accept OS update prompts** from the calculator.
2. **Do not connect to TI Connect CE / HP Connectivity Kit** if it auto-updates.
3. **Document your current OS version** (accessible in the calculator's About or Version menu).

### Calculator vs. Computer Flashing

Unlike microcontrollers, calculators typically do not expose JTAG/SWD headers on their main boards. The jailbreak entry points are software exploits in the OS, not hardware-level access. This makes them version-dependent and patchable by the manufacturer.

---

## Links

| Resource | URL |
|---------|-----|
| arTIfiCE jailbreak (TI-84 Plus CE) | https://yvantt.github.io/arTIfiCE/ |
| Cesium shell (TI-84 Plus CE) | https://github.com/mateoconlechuga/cesium |
| Ndless (TI-Nspire) | https://ndless.me/ |
| TI-Nspire Linux | https://github.com/tangrs/nspire-linux |
| Omega firmware (NumWorks) | https://getomega.dev/ |
| Upsilon firmware (NumWorks) | https://getupsilon.web.app/ |
| Cemu (TI calculator emulator) | https://github.com/CE-Programming/CEmu |
| TI-Planet (community resource) | https://tiplanet.org/ |
