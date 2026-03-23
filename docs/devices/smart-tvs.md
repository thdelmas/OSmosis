# Smart TVs & Streaming Devices

OSmosis documents research, rooting methods, and homebrew access for smart TV platforms and streaming devices. This page covers every supported platform, known exploits, tools, and current research status.

**Important:** Modifying TV firmware may void your warranty and, on some platforms, can break DRM-dependent services (Netflix, Disney+, etc). Verify compatibility before proceeding.

---

## Support Status Overview

| Platform | Status | Primary Method |
|----------|--------|----------------|
| Samsung Smart TV (Tizen) | Research | SamyGO extensions, SSH dev mode |
| LG Smart TV (webOS) | Research | Homebrew Channel via rootmy.tv exploits |
| Android TV / Google TV (boxes) | Planned | ADB + Magisk |
| Android TV / Google TV (built-in panels) | Research | UART/serial |
| Amazon Fire TV Stick | Planned | ADB + Magisk, debloat |
| Roku | Research | RootMyRoku (patched in OS 10+), dev mode sideload |
| Apple TV HD / 4K 1st gen | Research | palera1n (checkm8, semi-tethered) |
| Apple TV 4K 2nd gen and later | Not supported | No known exploit |

---

## Samsung Smart TVs (Tizen)

Samsung's current smart TV platform runs [Tizen OS](https://www.tizen.org/). Full ROM replacement is not possible. The [SamyGO](https://www.samygo.tv/) project provides extensions and modifications that run alongside the stock firmware.

| Feature | Details |
|---------|---------|
| **OS** | Tizen (Samsung proprietary) |
| **ROM replacement** | Not possible |
| **Extensions** | SamyGO — custom apps, patches, and tweaks on top of stock Tizen |
| **SSH access** | Developer mode enables SSH on older firmware; removed in some 2024+ firmware versions |
| **Status** | Research |

### Key Details

- **SamyGO:** The longest-running Samsung TV modification project. Provides a package manager for extensions, ADB-style remote access on supported models, and patches for region locks and smart hub limitations. See [samygo.tv](https://www.samygo.tv/).
- **Developer mode:** Enabled via `SmartHub > Settings > Terms & Policy` (model-dependent). Provides SSH access and sideloading of Tizen apps on older firmware. Not available on all 2024+ models.
- **Tizen app sideloading:** Tizen `.wgt` packages can be installed via the Tizen SDK or SamyGO on developer-mode TVs without full root.
- **No kernel access:** Tizen's security model on current hardware prevents kernel-level modification. SamyGO operates entirely at the userspace/app layer.

---

## LG Smart TVs (webOS)

LG's smart TV platform is [webOS](https://webostv.developer.lge.com/). The [webosbrew](https://webosbrew.org/) community maintains the [Homebrew Channel](https://github.com/webosbrew/webos-homebrew-channel) and several root exploits.

| Feature | Details |
|---------|---------|
| **OS** | webOS (LG proprietary, based on Linux) |
| **ROM replacement** | Not possible |
| **Homebrew** | Homebrew Channel via [webosbrew.org](https://webosbrew.org/) |
| **Status** | Research |

### Root Exploits

| Exploit | webOS Versions | Status | Notes |
|---------|---------------|--------|-------|
| **RootMyTV v1** | webOS 4.x–5.x | Patched mid-2022 | Original rootmy.tv exploit |
| **RootMyTV v2** | webOS 5.x–6.x | Patched mid-2022 | Second-generation exploit |
| **faultmanager-autoroot** | webOS 4.0+ | Active (as of Jan 2025) | Leverages a fault manager service vulnerability |
| **dejavuln-autoroot** | Various | Active | Alternative autoroot method maintained by webosbrew |

Before attempting to root, check [CanI.RootMy.TV](https://cani.rootmy.tv/) — enter your exact model number and current firmware version to see which exploits apply.

### Key Details

- **Homebrew Channel:** Once root is obtained, the [Homebrew Channel](https://github.com/webosbrew/webos-homebrew-channel) provides a package manager for webOS apps, daemons, and patches. Maintained at [webosbrew.org](https://webosbrew.org/).
- **rootmy.tv:** The original one-click root site for LG TVs. The v1/v2 exploits it hosted are patched on current firmware, but the site redirects to current community resources. See [rootmy.tv](https://rootmy.tv/).
- **SSH access:** Root provides full SSH access to the underlying Linux system.
- **DRM services:** Netflix and other DRM-dependent services typically continue to work after rooting via Homebrew Channel, as the exploit does not modify the signed OS partition.
- **Firmware updates:** Applying OTA updates after rooting may patch the exploit and remove Homebrew Channel. Use the channel's built-in update blocker if you want to stay rooted.

---

## Android TV / Google TV

### Streaming Boxes (NVIDIA Shield, Xiaomi Mi Box, Generic Android TV)

Dedicated Android TV and Google TV boxes run a full Android userspace and are the most accessible targets for customization.

| Device | Chipset | Flash Method | Status |
|--------|---------|-------------|--------|
| NVIDIA Shield TV (2019) | Tegra X1+ | ADB + Magisk | Planned |
| NVIDIA Shield TV Pro | Tegra X1+ | ADB + Magisk | Planned |
| Xiaomi Mi Box S | Amlogic S905X | ADB + Magisk | Planned |
| Generic Android TV boxes | Various (Amlogic, Rockchip, Allwinner) | ADB + Magisk / SD card | Planned |

### Key Details

- **ADB access:** Enable developer mode (`Settings > About > Android TV OS build`, tap 7 times), then enable USB debugging. Connect via `adb connect <ip>` or USB.
- **Magisk:** Root is achieved by patching the boot image with [Magisk](https://github.com/topjohnwu/Magisk) and flashing via fastboot or ADB, depending on the device. Provides systemless root and module support.
- **Custom ROMs:** Several Amlogic and Rockchip-based boxes support custom Android TV ROMs. Community builds available on XDA and device-specific forums.
- **NVIDIA Shield:** Developer-friendly with an unlockable bootloader. Fastboot access available. Strong LineageOS community presence.
- **Google TV (Chromecast with Google TV):** ADB sideloading works for app installation. Root requires bootloader unlock, which is not officially supported on Chromecast hardware.

### Built-in TV Panels (Android TV integrated into display hardware)

TVs with Android TV or Google TV built into the panel (Sony Bravia, TCL, Hisense, etc.) are significantly more restricted than standalone boxes.

| Platform | Status | Notes |
|----------|--------|-------|
| Sony Bravia (Android TV) | Research | Some models have accessible UART pads |
| TCL (Android TV / Google TV) | Research | UART access documented on select models (XDA) |
| Hisense (Android TV / VIDAA) | Research | VIDAA-based models are separate OS; Android TV models vary |

### Key Details

- **UART/serial access:** Many integrated panels expose UART debug pads on the main board. These allow ADB-over-serial access without network connectivity, and on some models provide a root shell at boot. Requires opening the TV and locating the debug header.
- **Bootloader lock:** Built-in panels are typically shipped with locked bootloaders and no OEM unlock option. UART/serial is often the only practical entry point.
- **Fastboot:** Rarely accessible on integrated panels without prior UART root.

---

## Amazon Fire TV Stick

Amazon's Fire TV runs FireOS, a heavily modified Android fork. Amazon actively patches root methods in a cat-and-mouse cycle.

| Device | FireOS | Flash Method | Status |
|--------|--------|-------------|--------|
| Fire TV Stick 4K | FireOS 7+ | ADB + Magisk (older FireOS) | Planned |
| Fire TV Stick 4K Max | FireOS 7+ | ADB + Magisk (older FireOS) | Planned |
| Fire TV Stick Lite | FireOS 7+ | ADB + Magisk (older FireOS) | Planned |
| Fire TV Cube | FireOS 7+ | ADB + Magisk (older FireOS) | Planned |

### Key Details

- **ADB access:** Developer options available under `Settings > My Fire TV > Developer Options`. Enable ADB debugging and connect via `adb connect <ip>`. No USB debugging requires a workaround on current firmware.
- **Root via Magisk:** Older FireOS versions (pre-7.x) are rootable by patching the boot image with Magisk. Amazon patches exploits regularly; current FireOS versions have no public root method. Check [AFTVnews](https://www.aftvnews.com/) for up-to-date root status.
- **Launcher Manager exploit:** A system privilege escalation via Launcher Manager v1.1.1 allowed persistent custom launcher installation without root on some firmware versions. Amazon patched this; the patch/re-exploit cycle continues. See AFTVnews for current status.
- **Custom launchers:** Even without root, ADB sideloading allows installing alternative launchers (Wolf Launcher, ATV Experience). These can be set as default on some firmware versions.
- **Debloat:** ADB `pm disable-user` commands can disable Amazon bloatware without root. Scripts available in the Fire TV community on XDA.
- **AFTVnews:** The authoritative source for Fire TV rooting and hacking news. See [aftvnews.com](https://www.aftvnews.com/).

---

## Roku

Roku OS is a proprietary, closed platform with no official developer root access. A limited root exploit existed for one specific firmware version.

| Device | OS Version | Method | Status |
|--------|-----------|--------|--------|
| Realtek WiFi chip models (OS 9.4.0 build 4200 only) | 9.4.0 | RootMyRoku | Research |
| All other models / firmware | Any | Developer mode (sideload only) | Research |

### Key Details

- **RootMyRoku:** A one-time root exploit targeting Roku OS 9.4.0 build 4200, limited to Roku devices with Realtek WiFi chips. Patched in OS 10 and all subsequent releases. No current root method exists for OS 10+. See [RootMyRoku](https://github.com/fulldecent/rootmyroku) for historical documentation.
- **Developer mode:** All Roku devices support a developer mode that allows sideloading test channels (`.zip` packages). Enable via the remote keysequence: `Home x3, Up, Right, Left, Right, Left, Right`. Provides a web-based package installer on port 80 of the Roku's IP. Does not provide root or system access.
- **Firmware version lock:** Roku devices auto-update and there is no user-accessible mechanism to prevent OS updates or downgrade firmware.
- **Custom OS:** Not possible on current hardware. Roku uses a proprietary SoC configuration with no accessible bootloader.

---

## Apple TV

### Apple TV HD and Apple TV 4K (1st generation)

These models use Apple A-series chips affected by the checkm8 hardware-level bootrom exploit, making them jailbreakable with [palera1n](https://palera.in/).

| Device | Chip | Jailbreak | Type | Status |
|--------|------|-----------|------|--------|
| Apple TV HD (5th gen, 2015) | A8 | palera1n | Semi-tethered | Research |
| Apple TV 4K 1st gen (2017) | A10X Fusion | palera1n | Semi-tethered | Research |

### Key Details

- **palera1n:** Uses the [checkm8](https://github.com/axi0mX/ipwndfu) bootrom exploit (hardware-level, unpatchable via software update) to jailbreak compatible Apple devices. Semi-tethered means the jailbreak must be re-applied after each reboot using a computer. See [palera.in](https://palera.in/).
- **checkm8:** A USB DFU-mode vulnerability in Apple's T8010 (A10X) and T7000 (A8) bootroms. Because it is in read-only ROM, it cannot be patched by Apple via firmware updates.
- **tvOS:** After jailbreak, Sileo or Cydia can be used as package managers. Community repos provide tweaks and tools for tvOS.
- **SSH access:** Available post-jailbreak via OpenSSH from the Sileo/Cydia package manager.
- **Persistent root:** Root is accessible while jailbroken. A computer running palera1n is required after each reboot to re-enter the jailbroken state.

### Apple TV 4K (2nd generation and later)

No jailbreak is available for these models.

| Device | Chip | Status | Notes |
|--------|------|--------|-------|
| Apple TV 4K 2nd gen (2021) | A12 (T8020) | Not supported | Not vulnerable to checkm8 |
| Apple TV 4K 3rd gen (2022) | A15 (T8110) | Not supported | Not vulnerable to checkm8 |

- **T8020 / T8110:** These chips are not affected by checkm8 or any other public bootrom exploit. No jailbreak exists and none is anticipated from currently known vulnerabilities.

---

## External Resources

| Resource | URL | Notes |
|----------|-----|-------|
| SamyGO | [samygo.tv](https://www.samygo.tv/) | Samsung Tizen TV extensions and modifications |
| rootmy.tv | [rootmy.tv](https://rootmy.tv/) | LG webOS root — original exploit site, now redirects to community resources |
| webosbrew | [webosbrew.org](https://webosbrew.org/) | LG webOS homebrew community, active exploit maintenance |
| Homebrew Channel (webOS) | [github.com/webosbrew/webos-homebrew-channel](https://github.com/webosbrew/webos-homebrew-channel) | Package manager for rooted LG TVs |
| CanI.RootMy.TV | [cani.rootmy.tv](https://cani.rootmy.tv/) | Check LG TV model + firmware compatibility with available exploits |
| RootMyRoku | [github.com/fulldecent/rootmyroku](https://github.com/fulldecent/rootmyroku) | Historical Roku root exploit (OS 9.4.0 only, patched) |
| palera1n | [palera.in](https://palera.in/) | checkm8-based jailbreak for Apple TV HD and 4K 1st gen |
| AFTVnews | [aftvnews.com](https://www.aftvnews.com/) | Authoritative Fire TV rooting, hacking, and modification news |
