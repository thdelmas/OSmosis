## Credits & Acknowledgments

Osmosis is a wrapper and integration layer — the real work happens in the
upstream tools and communities we depend on. We wouldn't exist without them.

### Tools we wrap

| Tool | Authors / Project | What Osmosis uses it for |
|------|-------------------|--------------------------|
| [Heimdall](https://github.com/Benjamin-Dobell/Heimdall) | Benjamin Dobell | Samsung device flashing (Download Mode) |
| [fastboot / adb](https://developer.android.com/tools) | Google / Android Open Source Project | Pixel & generic Android flashing, sideloading |
| [debootstrap](https://wiki.debian.org/Debootstrap) | Debian project | OS Builder: Debian/Ubuntu rootfs bootstrap |
| [pacstrap](https://man.archlinux.org/man/pacstrap.8) | Arch Linux | OS Builder: Arch Linux installs |
| [dnf](https://github.com/rpm-software-management/dnf) | Fedora / RPM community | OS Builder: Fedora rootfs bootstrap |
| [Nix](https://nixos.org/) | NixOS Foundation | OS Builder: NixOS image builds |
| [Magisk](https://github.com/topjohnwu/Magisk) | topjohnwu | Boot image patching for root access |
| [bleak](https://github.com/hbldh/bleak) | Henrik Blidh | Bluetooth Low Energy communication for scooters |
| [OpenOCD / st-flash](https://openocd.org/) | OpenOCD community | ST-Link hardware flashing for scooters |

### ROM & firmware projects

| Project | Link | Role |
|---------|------|------|
| [LineageOS](https://lineageos.org/) | lineageos.org | Custom ROM for Samsung, Pixel, and many others |
| [GrapheneOS](https://grapheneos.org/) | grapheneos.org | Privacy-focused ROM for Pixel devices |
| [CalyxOS](https://calyxos.org/) | calyxos.org | Privacy ROM for Pixel devices |
| [/e/OS](https://e.foundation/) | e.foundation | De-Googled Android ROM |
| [PostmarketOS](https://postmarketos.org/) | postmarketos.org | Real Linux on phones |
| [TWRP](https://twrp.me/) | Team Win | Custom recovery for Android devices |

### Scooter community

The scooter flashing support in Osmosis is built entirely on the research and
tools of the **[ScooterHacking](https://scooterhacking.org/)** community:

- **CFW builders** at [cfw.sh](https://cfw.sh/), [max.cfw.sh](https://max.cfw.sh/), [mi.cfw.sh](https://mi.cfw.sh/), [esx.cfw.sh](https://esx.cfw.sh/), [pro2.cfw.sh](https://pro2.cfw.sh/) — maintained by the ScooterHacking team
- **Protocol documentation**: [ninebot-docs](https://github.com/etransport/ninebot-docs/wiki/protocol) (etransport), [M365-BLE-PROTOCOL](https://github.com/CamiAlfa/M365-BLE-PROTOCOL) (CamiAlfa)
- **ScooterHacking Utility** app and NinebotCrypto research — reverse engineering that made BLE flashing possible
- **[ScooterFlasher](https://github.com/Encryptize/scooterflasher)** (Encryptize) — OpenOCD wrapper reference
- **[LibreScoot](https://librescoot.org/)** — open-source firmware for unu Scooter Pro
- **Bastelpichi wiki** — Xiaomi Mi 4 Pro / Brightway documentation
- **bw-flasher / bw-patcher** — Brightway platform flashing tools

See [docs/reverse-engineering-communities.md](docs/reverse-engineering-communities.md) for the full directory of communities and tools.

### Also built on

- [Flask](https://palletsprojects.com/p/flask/) (Pallets) — web backend
- [Vue 3](https://vuejs.org/) — frontend framework
- [Vite](https://vite.dev/) — build tooling
- [vue-i18n](https://vue-i18n.intlify.dev/) — internationalization

If we missed crediting your work, please [open an issue](https://github.com/thdelmas/FlashWizard/issues) — we want to get this right.

