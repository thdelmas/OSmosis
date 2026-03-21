# Single-Board Computers (SBCs)

OSmosis supports writing OS images and managing firmware for a wide range of single-board computers. SBCs are flashed by writing an OS image to an SD card or eMMC module, then booting from it.

---

## Raspberry Pi

The most popular SBC family. Raspberry Pi boards are supported by a massive ecosystem of operating systems and software.

### Devices

| Device | SoC | RAM | Boot Method | OSmosis Support |
|--------|-----|-----|-------------|----------------|
| Raspberry Pi 5 | BCM2712 (Cortex-A76) | 4/8 GB | microSD / NVMe | Supported |
| Raspberry Pi 4 Model B | BCM2711 (Cortex-A72) | 1/2/4/8 GB | microSD / USB | Supported |
| Raspberry Pi 400 | BCM2711 (Cortex-A72) | 4 GB | microSD | Supported |
| Raspberry Pi 3 Model B+ | BCM2837B0 (Cortex-A53) | 1 GB | microSD | Supported |
| Raspberry Pi 3 Model B | BCM2837 (Cortex-A53) | 1 GB | microSD | Supported |
| Raspberry Pi Zero 2 W | RP3A0 (Cortex-A53) | 512 MB | microSD | Supported |
| Raspberry Pi Zero W | BCM2835 (ARM1176JZF-S) | 512 MB | microSD | Supported |

### OS Compatibility

| OS | Supports | Description |
|----|----------|-------------|
| **Raspberry Pi OS** | All models | Official Debian-based OS. 32-bit and 64-bit. Recommended for most users. |
| **Ubuntu** | Pi 3+, 4, 5 | Official Canonical builds. Server and Desktop editions. |
| **Ubuntu Core** | Pi 3+, 4, 5 | Snap-based, IoT-focused Ubuntu. |
| **Manjaro ARM** | Pi 4, 5 | Arch-based rolling release with multiple desktop options. |
| **Fedora** | Pi 3+, 4, 5 | Official Fedora ARM builds. Server, Workstation, IoT. |
| **DietPi** | All models | Lightweight Debian-based. Optimized for low-resource SBCs. |
| **LibreELEC** | Pi 3+, 4, 5 | Kodi-based media center OS. |
| **OSMC** | Pi 3+, 4 | Another Kodi-based media center. |
| **Home Assistant OS** | Pi 3+, 4, 5 | Smart home platform. Dedicated OS image. |
| **OctoPrint** | Pi 3+, 4, 5 | 3D printer management (OctoPi image). |
| **RetroPie** | All models | Retro gaming emulation platform. |
| **Recalbox** | All models | Alternative retro gaming platform. |
| **Kali Linux** | Pi 3+, 4, 5 | Security/pentesting distribution. |
| **Twister OS** | Pi 4, 5 | Desktop-focused with theming (Windows/macOS look). |

### Key Details

- **Pi 5:** First to support NVMe via the official M.2 HAT. Significant performance jump over Pi 4.
- **Pi 4 USB boot:** Requires bootloader update to boot from USB drives or SSDs.
- **Pi 400:** Keyboard-integrated Pi 4. Same SoC and compatibility.
- **Pi Zero 2 W:** Quad-core upgrade over the original Zero W. Same form factor.
- **Pi Zero W:** Single-core ARM11. Suitable for lightweight headless projects only.
- **Official imager:** Raspberry Pi Imager (`rpi-imager`) handles OS selection, SD writing, and pre-configuration (WiFi, SSH, hostname).

---

## Pine64 SBCs

Pine64 produces a range of open-hardware SBCs with strong community Linux support.

### Devices

| Device | SoC | RAM | Boot Method | OSmosis Support |
|--------|-----|-----|-------------|----------------|
| ROCK64 | RK3328 (Cortex-A53) | 1/2/4 GB | microSD / eMMC | Supported |
| ROCKPro64 | RK3399 (A72+A53) | 2/4 GB | microSD / eMMC / NVMe | Supported |
| Quartz64 Model A | RK3566 (Cortex-A55) | 4/8 GB | microSD / eMMC | Supported |
| PineBook Pro | RK3399 (A72+A53) | 4 GB | eMMC / microSD | Supported |

### OS Compatibility

| OS | Supports | Description |
|----|----------|-------------|
| **Armbian** | All Pine64 SBCs | Debian/Ubuntu-based. Widest hardware support. Recommended. |
| **Manjaro ARM** | ROCKPro64, PineBook Pro | Arch-based with KDE, XFCE, or Sway. |
| **Debian** | ROCK64, ROCKPro64 | Official Debian ARM images. |
| **DietPi** | ROCK64, ROCKPro64 | Lightweight Debian. |
| **LibreELEC** | ROCK64 | Kodi media center. |

### Key Details

- **ROCKPro64:** Flagship Pine64 SBC. PCIe x4 slot for NVMe or other cards. Popular for NAS builds.
- **PineBook Pro:** ARM laptop with 14" display, RK3399, and 64GB eMMC. Runs Manjaro ARM or Armbian.
- **Quartz64:** RK3566-based, newer design with PCIe and improved mainline kernel support.
- **ROCK64:** Budget board. Good for media servers and lightweight tasks.

---

## Orange Pi SBCs

Orange Pi offers high-performance SBCs at competitive prices, often using Rockchip or Allwinner SoCs.

### Devices

| Device | SoC | Key Features | OSmosis Support |
|--------|-----|-------------|----------------|
| Orange Pi 5 | RK3588S | 4-32 GB RAM, NVMe | Supported |
| Orange Pi 5 Plus | RK3588 | Dual GbE, HDMI 2.1, NVMe | Supported |
| Orange Pi Zero 3 | Allwinner H618 | WiFi/BT, compact | Supported |

### OS Compatibility

| OS | Supports | Description |
|----|----------|-------------|
| **Armbian** | All Orange Pi models | Recommended. Best driver support. |
| **Orange Pi OS** | All models | Official Android or Debian-based images from Orange Pi. |
| **Ubuntu** | OPi 5, 5 Plus | Community images. |
| **Debian** | All models | Via Armbian or direct. |

### Key Details

- **Orange Pi 5:** RK3588S makes this one of the most powerful affordable SBCs. Comparable to a mid-range desktop for many tasks.
- **Orange Pi 5 Plus:** Full RK3588 with dual Gigabit Ethernet — popular for router and NAS use.
- **Orange Pi Zero 3:** Budget option for IoT and lightweight servers.

---

## Radxa SBCs

Radxa produces high-end SBCs centered on the RK3588 platform.

### Devices

| Device | SoC | Key Features | OSmosis Support |
|--------|-----|-------------|----------------|
| ROCK 5B | RK3588 | Full-size, PCIe 3.0 x4, HDMI 2.1 | Supported |
| ROCK 5A | RK3588S | Compact, M.2 for WiFi/NVMe | Supported |

### OS Compatibility

| OS | Supports | Description |
|----|----------|-------------|
| **Armbian** | Both models | Recommended. Active kernel development. |
| **Radxa Debian** | Both models | Official Radxa images based on Debian. |
| **Ubuntu** | Both models | Community and Radxa-provided images. |
| **Android 12** | Both models | Official Radxa Android images. |

### Key Details

- **ROCK 5B:** One of the most powerful ARM SBCs available. 8K video output, PCIe 3.0 x4, up to 16 GB RAM.
- **ROCK 5A:** Same RK3588S as Orange Pi 5 in a more compact form factor.

---

## ODROID SBCs

Hardkernel's ODROID boards are known for reliability and strong community support.

### Devices

| Device | SoC | Key Features | OSmosis Support |
|--------|-----|-------------|----------------|
| ODROID-N2+ | Amlogic S922X | Hexa-core, 4 GB RAM | Supported |
| ODROID-M1 | RK3568B2 | NVMe, SATA, 8 GB RAM | Supported |
| ODROID-C4 | Amlogic S905X3 | Quad-core, 4 GB RAM | Supported |

### OS Compatibility

| OS | Supports | Description |
|----|----------|-------------|
| **Armbian** | All ODROID models | Recommended for server/desktop use. |
| **Ubuntu** | N2+, M1 | Official Hardkernel Ubuntu images. |
| **Android** | N2+, C4 | Official Hardkernel Android images. |
| **CoreELEC** | N2+, C4 | Kodi media center (Amlogic-optimized). |
| **DietPi** | All models | Lightweight Debian. |
| **Home Assistant** | N2+, M1 | Officially recommended SBC for Home Assistant. |

### Key Details

- **ODROID-N2+:** Long-time Home Assistant recommended board. Excellent stability.
- **ODROID-M1:** RK3568-based with NVMe and SATA — great for NAS.
- **ODROID-C4:** Budget Amlogic board. Good for media and light tasks.

---

## NVIDIA Jetson

NVIDIA's Jetson platform is designed for AI/ML inference at the edge. These boards run NVIDIA's JetPack SDK on Ubuntu.

### Devices

| Device | SoC | GPU | Key Features | OSmosis Support |
|--------|-----|-----|-------------|----------------|
| Jetson Nano | Tegra X1 | 128-core Maxwell | 4 GB RAM, CUDA | Supported |
| Jetson Orin Nano | Orin | 1024-core Ampere | 4/8 GB RAM, up to 40 TOPS | Supported |

### OS Compatibility

| OS | Description |
|----|-------------|
| **JetPack (Ubuntu-based)** | Official NVIDIA SDK. Includes CUDA, cuDNN, TensorRT. Required for GPU workloads. |
| **Armbian** | Community support for Jetson Nano. No GPU acceleration. |
| **DietPi** | Lightweight option. No GPU acceleration. |

### Key Details

- **JetPack is required for AI/ML workloads.** Without it, the GPU is unused.
- **Jetson Nano:** Entry-level AI board. Widely used in robotics and computer vision projects.
- **Jetson Orin Nano:** Massive performance upgrade. Up to 80x the AI performance of the original Nano.
- **SDK Manager:** NVIDIA's SDK Manager tool handles flashing JetPack to the board.

---

## RISC-V SBCs (Emerging)

These are early RISC-V boards with growing but still limited OS support. Listed for forward-looking users and developers.

### Devices

| Device | SoC | Key Features | OSmosis Support |
|--------|-----|-------------|----------------|
| StarFive VisionFive 2 | JH7110 | Quad-core RISC-V, GbE, GPU | Supported |
| Milk-V Mars | JH7110 | Same SoC as VisionFive 2, compact | Supported |
| Sipeed LicheeRV Dock | Allwinner D1 | Single-core RISC-V, budget | Supported |

### OS Compatibility

| OS | Supports | Description |
|----|----------|-------------|
| **Debian** | VisionFive 2, Milk-V Mars | Official StarFive Debian images. Best supported. |
| **Ubuntu** | VisionFive 2 | Canonical preview images. |
| **Fedora** | VisionFive 2 | Fedora RISC-V SIG builds. |
| **openSUSE** | VisionFive 2 | Tumbleweed RISC-V. |
| **Armbian** | VisionFive 2 | Early support. |

### Key Details

- **JH7110:** The most capable RISC-V SoC currently available in consumer boards. Quad-core SiFive U74, GPU, 1080p video.
- **Allwinner D1:** Single-core XuanTie C906. Very limited but historically significant as one of the first affordable RISC-V Linux boards.
- **Software maturity:** RISC-V Linux support is improving rapidly but expect more rough edges than ARM boards. Some packages may not be available.
- **Why RISC-V?** Open instruction set architecture — no licensing fees, fully auditable, no proprietary CPU microcode.

---

## General Notes for SBCs

### Choosing an OS

- **General purpose / server:** Armbian (Debian or Ubuntu variant) has the widest board support and best driver integration.
- **Raspberry Pi:** Raspberry Pi OS is the path of least resistance. Ubuntu for server workloads.
- **Media center:** LibreELEC or CoreELEC (Amlogic boards).
- **Home automation:** Home Assistant OS on Pi 4/5 or ODROID-N2+.
- **AI/ML:** JetPack on Jetson. No substitute.

### Flashing Process

1. Download the OS image from the project's website
2. Write the image to a microSD card or eMMC module using `dd`, `balenaEtcher`, Raspberry Pi Imager, or OSmosis
3. Insert the media and power on the board
4. Some boards (Pi 4/5, ROCKPro64) support NVMe boot — flash to NVMe and update the bootloader
