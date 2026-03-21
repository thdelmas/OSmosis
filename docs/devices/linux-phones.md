# Linux Phones

OSmosis supports a family of devices designed to run mainline Linux distributions natively, rather than Android. These devices boot from SD cards or eMMC and can run multiple Linux-based mobile operating systems.

---

## PinePhone

The original PinePhone is a community-driven Linux phone from Pine64. It is the most widely supported device in the Linux phone ecosystem.

| Field | Value |
|-------|-------|
| **Manufacturer** | Pine64 |
| **SoC** | Allwinner A64 (quad-core Cortex-A53) |
| **RAM** | 2 GB / 3 GB |
| **Storage** | 16 GB / 32 GB eMMC + microSD |
| **Display** | 5.95" IPS, 1440x720 |
| **Boot method** | microSD card or eMMC |
| **OSmosis support** | Supported |

### OS Compatibility

| OS | Description | Status |
|----|-------------|--------|
| **Mobian** | Debian-based, Phosh UI | Actively maintained. Recommended for stability. |
| **postmarketOS** | Alpine-based, multiple UI options | Actively maintained. Supports Phosh, Plasma Mobile, Sxmo. |
| **Manjaro ARM** | Arch-based, Plasma Mobile or Phosh | Community maintained. |
| **Arch Linux ARM** | Rolling release, DIY | Community maintained. For advanced users. |
| **Ubuntu Touch** | Unity-based mobile OS | UBports community. Functional but fewer updates. |
| **Sailfish OS** | Jolla's mobile Linux | Community port. Proprietary UI layer. |
| **Nemo Mobile** | Open-source Sailfish alternative | Early stage. |
| **LuneOS** | webOS successor | Experimental. |

### Key Details

- **Hardware kill switches:** 6 DIP switches on the back cover to disable modem, WiFi/BT, microphone, rear camera, front camera, and headphone jack
- **Convergence:** Connect to a monitor via USB-C dock for a desktop experience
- **Dual boot:** Flash one OS to eMMC and another to microSD — boot order prioritizes SD
- **Pogo pins:** Back cover expansion connector for keyboard case, LoRa, wireless charging, etc.

---

## PinePhone Pro

The PinePhone Pro is the higher-performance successor with an RK3399 SoC.

| Field | Value |
|-------|-------|
| **Manufacturer** | Pine64 |
| **SoC** | Rockchip RK3399 (dual Cortex-A72 + quad Cortex-A53) |
| **RAM** | 4 GB |
| **Storage** | 128 GB eMMC + microSD |
| **Display** | 6" IPS, 1440x720 |
| **Boot method** | microSD card or eMMC |
| **OSmosis support** | Supported |

### OS Compatibility

| OS | Description | Status |
|----|-------------|--------|
| **postmarketOS** | Alpine-based | Primary recommended OS. Best hardware support. |
| **Mobian** | Debian-based | Actively maintained. |
| **Manjaro ARM** | Arch-based | Community maintained. |
| **Arch Linux ARM** | Rolling release | Community maintained. |

### Key Details

- **Same form factor** as PinePhone — compatible with PinePhone accessories and cases
- **Hardware kill switches:** Same 6-switch configuration as the original
- **Better performance:** RK3399 is significantly faster than A64, making daily use more practical
- **GPU:** Mali-T860 MP4 with Panfrost open-source driver

---

## PineTab 2

The PineTab 2 is Pine64's Linux tablet, powered by a Rockchip RK3566.

| Field | Value |
|-------|-------|
| **Manufacturer** | Pine64 |
| **SoC** | Rockchip RK3566 (quad-core Cortex-A55) |
| **RAM** | 4 GB / 8 GB |
| **Storage** | 64 GB / 128 GB eMMC + microSD |
| **Display** | 10.1" IPS, 1280x800 |
| **Boot method** | microSD card or eMMC |
| **OSmosis support** | Supported |

### OS Compatibility

| OS | Description | Status |
|----|-------------|--------|
| **postmarketOS** | Alpine-based | Primary recommended OS. |
| **Mobian** | Debian-based | In development. |
| **Arch Linux ARM** | Rolling release | Community images available. |

### Key Details

- **Detachable keyboard:** Magnetic keyboard attachment for laptop-style use
- **RK3566:** Lower power consumption than RK3399 but also lower peak performance
- **Use case:** Linux tablet for reading, browsing, light development, and media

---

## Librem 5

The Librem 5 from Purism is a privacy-focused Linux phone running PureOS by default.

| Field | Value |
|-------|-------|
| **Manufacturer** | Purism |
| **SoC** | NXP i.MX 8M Quad (quad-core Cortex-A53) |
| **RAM** | 3 GB |
| **Storage** | 32 GB eMMC + microSD |
| **Display** | 5.7" IPS, 720x1440 |
| **Boot method** | eMMC or microSD |
| **OSmosis support** | Supported |

### OS Compatibility

| OS | Description | Status |
|----|-------------|--------|
| **PureOS** | Purism's Debian-based OS with Phosh | Default OS. Actively maintained by Purism. |
| **Mobian** | Debian-based | Well supported. |
| **postmarketOS** | Alpine-based | Supported. |

### Key Details

- **Hardware kill switches:** 3 physical switches on the side for WiFi/BT, cellular modem, and camera/microphone
- **Separate chips:** WiFi, cellular modem, and GPS are on separate, removable M.2 cards — not integrated into the SoC
- **Privacy by design:** No proprietary blobs in the SoC (i.MX 8M has open-source GPU drivers via etnaviv)
- **Convergence:** USB-C dock support for desktop mode
- **Smart card reader:** Built-in OpenPGP smart card support

---

## General Notes for Linux Phones

### Choosing an OS

- **New to Linux phones?** Start with **Mobian** (Debian-based, familiar package management) or **postmarketOS** (lightweight, well-documented).
- **Want the latest packages?** Choose **Manjaro ARM** or **Arch Linux ARM** for rolling releases.
- **Privacy-focused?** **PureOS** on Librem 5 or **postmarketOS** on PinePhone with full-disk encryption.

### Common UI Shells

| Shell | Description |
|-------|-------------|
| **Phosh** | GNOME-based mobile shell. Most polished. Default on Mobian and PureOS. |
| **Plasma Mobile** | KDE's mobile shell. Feature-rich but heavier. |
| **Sxmo** | Minimalist tiling WM for phones (dwm/sway). For power users. |

### Flashing Process

1. Download the OS image from the project's website
2. Write the image to a microSD card using `dd`, `balenaEtcher`, or similar
3. Insert the SD card and boot the device
4. Optionally, flash the OS from SD to internal eMMC for better performance
