# Samsung Galaxy Ace 2 (GT-I8160 / codina)

## Device Overview

| Spec | Value |
|---|---|
| SoC | ST-Ericsson NovaThor U8500 (dual Cortex-A9 @ 800MHz) |
| GPU | Mali-400 MP1 |
| RAM | 768 MB |
| Storage | 4 GB internal + microSD |
| Display | 3.8" 480x800 PLS TFT |
| Battery | 1500 mAh removable Li-Ion |
| USB | microUSB 2.0 |
| WiFi | BCM4330 (802.11 b/g/n) |
| Bluetooth | 3.1, A2DP (BCM4330) |
| NFC | PNX544 (GT-I8160P variant only, antenna in back plate) |
| GPS | Broadcom BCM4751 |
| Stock OS | Android 4.1.2 Jelly Bean (JZO54K.I8160XXMG2) |
| Release | May 2012 |

### Variants

| Model | Notes |
|---|---|
| GT-I8160 | International, base model |
| GT-I8160P | NFC-equipped variant |
| GT-I8160chn | Chinese market |
| GT-I8160I | Unknown region |
| GT-I8160L | Latin American |

## Boot Chain

```
Samsung PBL (ROM, read-only)
    → ISSW / X-Loader (TOC partition, read-only)
    → SBL (Secondary Boot Loader, read-only via Heimdall)
        → Normal boot: loads kernel from Kernel2 PIT partition
        → Recovery: loads from unknown location (not Kernel or Kernel2)
    → Linux kernel
    → Android init / ramdisk
```

### Critical Finding: Kernel2 is the Boot Partition

**The SBL loads the normal boot kernel from the `Kernel2` PIT partition (entry 9), NOT the `Kernel` partition (entry 6).**

This was proven by real-world testing on 2026-03-29:
- Flashing anything to `Kernel` (entry 6) has zero effect on boot behavior
- Flashing a mainline kernel to `Kernel2` (entry 9) causes boot-loops (kernel starts, panics, reboots)
- Zeroing `Kernel2` causes permanent Samsung logo hang
- The stock kernel was on `Kernel2` all along

The `Kernel` partition (entry 6) purpose is unknown — possibly unused or a legacy artifact.

### Recovery Kernel Location

The recovery kernel is NOT on `Kernel` or `Kernel2`. Evidence:
- After zeroing BOTH `Kernel` and `Kernel2`, recovery still boots via Vol Up + Home + Power
- Recovery enters "Manual Mode" with ADB sideload when normal boot fails
- The recovery kernel is likely embedded in the SBL or loaded from a raw eMMC offset not mapped in the PIT

## Partition Table (PIT)

Dumped via `heimdall download-pit` on 2026-03-29. CPU/bootloader tag: "Codina".

| Entry | Name | Offset (blk) | Count (blk) | Size | Attr | Flash Filename |
|---|---|---|---|---|---|---|
| 0 | TOC,ISSW,Xloader | 256 | 768 | 0.4 MB | RO | STE_boot.bin.md5 |
| 1 | STE Mem Init | 61440 | 1024 | 0.5 MB | RO | mem_init.bin.md5 |
| 2 | PWR MGT | 62464 | 1024 | 0.5 MB | RO | power_management.bin.md5 |
| 3 | IPL Modem | 104448 | 4096 | 2 MB | RO | ipl.bin.md5 |
| 4 | Modem | 108544 | 32768 | 16 MB | RW | modem.bin.md5 |
| 5 | SBL | 63488 | 4096 | 2 MB | **RO** | normal.bin.md5 |
| 6 | Kernel | 141312 | 32768 | 16 MB | RW | kernel.bin.md5 |
| 7 | MBR,GPT | 0 | 256 | 0.1 MB | RW | — |
| 8 | SBL_2 | 67584 | 4096 | 2 MB | RO | normal2.bin.md5 |
| 9 | **Kernel2** | **174080** | **32768** | **16 MB** | **RW** | **kernel2.bin.md5** |
| 10 | PARAM | 71680 | 32768 | 16 MB | RW | param.lfs.md5 |
| 11 | Modem FS | 28672 | 32768 | 16 MB | RW | modemfs.img.md5 |
| 12 | SYSTEM | 206848 | 1253376 | 612 MB | RW | system.img.md5 |
| 13 | CACHEFS | 4016128 | 626688 | 306 MB | RW | cache.img.md5 |
| 14 | DATAFS | 1460224 | 2555904 | 1248 MB | RW | userdata.img.md5 |
| 15 | CSPSA FS | 3072 | 3072 | 1.5 MB | RW | cspsa.img.md5 |
| 16 | EFS | 8192 | 20480 | 10 MB | RW | EFS.img.md5 |
| 17 | UMS | 5400576 | 2312192 | 1129 MB | RW | ums.rfs.md5 |
| 18 | HIDDEN | 4642816 | 655360 | 320 MB | RW | hidden.img.md5 |
| 19 | PIT | 1024 | 2048 | 1 MB | RW | GT-I8160_EUR_XX_4G.pit.md5 |
| 20 | Fota | 5298176 | 102400 | 50 MB | RW | ssgtest.img.md5 |

**Notes:**
- Entries 0-11 are at raw eMMC offsets (before GPT)
- Entries 12-20 are GPT partitions
- Block size = 512 bytes (Samsung standard)
- SBL and SBL_2 are read-only — Heimdall rejects writes with "Failed to confirm end of file transfer sequence"
- Full PIT saved at: `~/Osmosis-downloads/samsung-codina/codina-full.pit`

## Heimdall Quirks

- **Stale sessions**: Heimdall sessions go stale after one command. Cannot run `detect` then `flash` — must flash as the first command after a fresh USB connection.
- **SBL write protection**: The SBL partition rejects writes. Neither `--SBL` name nor numeric partition ID works.
- **Numeric partition IDs**: Using `--5` (numeric ID) crashes Heimdall with segfault (v2.0.2).
- **Multi-partition flash**: Flashing multiple partitions in one session works with `--resume` flag.
- **USB VID/PID**: Download Mode = `04e8:685d`, MTP/normal = `04e8:6860`.

## What We Tried (2026-03-29)

### Attempt 1: U-Boot to Kernel partition
- Flashed raw `u-boot.bin` (292K, built from stemmy defconfig) to `Kernel` (entry 6)
- **Result**: No effect. Phone boots to stock Android. Kernel partition is not in the boot path.

### Attempt 2: U-Boot wrapped in Android boot.img to Kernel
- Wrapped U-Boot in Android boot.img format with proper ANDROID! magic
- **Result**: No effect. Same as raw binary.

### Attempt 3: U-Boot with zImage magic patch to Kernel
- Patched offset 0x24 to contain ARM zImage magic (0x016F2818)
- **Result**: No effect.

### Attempt 4: U-Boot to BOTH Kernel AND Kernel2
- Flashed U-Boot to both partitions to eliminate fallback
- **Result**: Samsung logo hang. Phone doesn't boot. This proved Kernel2 IS the boot partition.

### Attempt 5: Mainline kernel (raw zImage, no DTB) to Kernel2
- Flashed pmOS kernel 6.18.2 (raw zImage) to Kernel2
- **Result**: Boot loop (USB device number cycles every 4-6 seconds). Kernel starts but panics immediately — no DTB.

### Attempt 6: Mainline kernel + appended DTB to Kernel2
- Concatenated vmlinuz + ste-ux500-samsung-codina.dtb
- **Result**: Samsung logo hang, stable (no boot-loop). Kernel loads but panics silently — no rootfs.

### Attempt 7: CyanogenMod kernel (no ramdisk) to Kernel2
- Built from `dh-harald/android_kernel_samsung_codina` with `cyanogenmod_i8160_defconfig`
- Required fixes: `cpu_is_u9500` inline removal, gnueabihf toolchain (not gnueabi)
- Disabled CONFIG_INITRAMFS_SOURCE (no ramdisk)
- **Result**: Samsung logo hang.

### Attempt 8: CyanogenMod kernel WITH embedded ramdisk to Kernel2
- Same kernel with busybox initramfs embedded via CONFIG_INITRAMFS_SOURCE
- **Result**: Samsung logo → **black screen** (first time). Kernel booted! Display initialized and cleared the Samsung logo. But Android init failed (ramdisk not compatible with stock system).

### Attempt 9: CyanogenMod kernel with ADB ramdisk to Kernel2
- Ramdisk with android_usb gadget switch to ADB mode
- **Result**: Samsung logo hang. No ADB.

### Attempt 10: CyanogenMod kernel with LETHE OS ramdisk to Kernel2
- Minimal ramdisk: busybox + USB RNDIS networking + telnetd
- **Result**: Samsung logo hang / intermittent black screen + reboot cycle.
- USB gadget never switches from Samsung MTP (04e8:6860) to RNDIS (0525:a4a7)
- Init script likely panics before reaching USB gadget configuration

### Recovery via ADB Sideload
- Stock Samsung recovery enters "Manual Mode" when boot fails
- Wipes data automatically, then waits for ADB sideload
- Rejects unsigned ZIPs (tested with jarsigner SHA256 self-signed cert)
- Rejects non-Samsung-format packages (tested with .tar.md5)
- Only accepts Samsung-signed OTA packages

## Building the CyanogenMod Kernel

### Working build environment
```
Docker image: ubuntu:14.04
Toolchain: gcc-arm-linux-gnueabihf (GCC 4.8.4)
Source: https://github.com/dh-harald/android_kernel_samsung_codina
Defconfig: cyanogenmod_i8160_defconfig
```

### Required patches
1. **cpu_is_u9500 inline fix**: `sed -i "s/inline bool cpu_is_u9500/bool cpu_is_u9500/" arch/arm/mach-ux500/include/mach/id.h`
2. **Toolchain**: Must use `gnueabihf` (hard float) not `gnueabi` — VFP assembly requires it
3. **GCC version**: Must be GCC 4.x. GCC 5+ fails with inlining errors. GCC 10+ fails with `compiler-gcc10.h` missing.

### Build command
```bash
docker run --rm -v $(pwd):/out ubuntu:14.04 bash -c '
apt-get update -qq && apt-get install -y -qq gcc gcc-arm-linux-gnueabihf make git bc cpio
git clone --depth=1 https://github.com/dh-harald/android_kernel_samsung_codina.git /tmp/kernel
cd /tmp/kernel
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- cyanogenmod_i8160_defconfig
sed -i "s/inline bool cpu_is_u9500/bool cpu_is_u9500/" arch/arm/mach-ux500/include/mach/id.h
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j$(nproc) zImage
cp arch/arm/boot/zImage /out/
'
```

### Stock kernel build (ddikodroid/samsung_codina_kernel)
- Defconfig: `GT-I8160_defconfig`
- **Does not compile**: Requires `ccache`, Samsung-specific Makefile patches, and a matching Android build environment. Not viable for standalone kernel builds.

## Restoring Stock Firmware

### Samsung FUS (Firmware Update Server)
- Samsung has removed ALL GT-I8160 firmware from their servers (HTTP 408 on every region)
- Tested all major regions: BTU, XEO, DBT, AUT, PHE, SER, XEF, ITV, XSP, THR, NEE, ATO, TUR, EUR, KSA
- `samloader` tool (v0.4, martinetd fork) confirms versions exist but cannot download

### Third-party firmware mirrors
- **sfirmware.com**: Site is live, has 100+ regional firmware variants. Requires JavaScript browser. Download links work (as of 2026-03-29).
- **sammobile.com**: Requires free account. Slow downloads.
- **Samsung FOTA XML**: `https://fota-cloud-dn.ospserver.net/firmware/BTU/GT-I8160/version.xml` still responds with version info but binary downloads are 403.

### Recommended recovery procedure
1. Download firmware from sfirmware.com (any region with Android 4.1.2 / I8160XXMG2)
2. Extract .zip → extract .tar.md5 → find `kernel2.bin.md5`
3. Enter Download Mode: Vol Down + Home + Power → Vol Up to confirm
4. Flash: `heimdall flash --Kernel2 kernel2.bin.md5`
5. If full restore needed, flash all partition images via Heimdall or use Odin on Windows

### Key firmware files inside .tar.md5
| File | Target Partition |
|---|---|
| kernel2.bin.md5 | Kernel2 (boot kernel) |
| system.img.md5 | SYSTEM |
| cache.img.md5 | CACHEFS |
| hidden.img.md5 | HIDDEN |
| modem.bin.md5 | Modem |
| param.lfs.md5 | PARAM |

## Secure Boot Status

Per leaked ST-Ericsson U8500 source code (`vendor_st-ericsson_u8500`):
- **Secure boot OTP fuses are NOT blown** on consumer Samsung U8500 devices
- `TEE_RT_FLAGS_SECURE_BOOT` (0x80) is clear — SBL accepts unsigned images
- The SBL does NOT enforce signature verification on boot images
- The boot failures we experienced were due to wrong partition (Kernel vs Kernel2), wrong image format, or kernel panics — NOT signature rejection

## postmarketOS Status

- **Tier**: Testing (edge channel only, not in stable releases)
- **pmOS device**: `samsung-codina`
- **Kernel**: `linux-postmarketos-stericsson` (mainline 6.18.2)
- **Flash method**: fastboot (requires U-Boot as intermediate bootloader)

### What works on pmOS (per wiki)
- Touchscreen, WiFi, 3D GPU (Lima), Bluetooth (manual bdaddr), proximity sensor, haptics

### What's broken on pmOS
- Display (DPI path, needs DT fix), audio (MSP not enabled), camera, GPS, modem

### OSmosis kernel patches
Located at `patches/samsung-codina/`:
- `0001-arm-dts-ux500-codina-enable-display-dpi-panel.patch` — MCDE DPI + WS2401 panel
- `0002-arm-dts-ux500-codina-enable-audio-msp-ab8500.patch` — MSP I2S + AB8500 codec

**These patches are untested** — we could not boot the mainline kernel on our test unit due to the Kernel2 partition discovery happening late in the process.

## Known Issues

### Battery brick risk (CRITICAL)
If the battery fully depletes, the device cannot charge because it cannot boot to the kernel, and it cannot boot if battery is too low. Recovery requires an external battery charger or a replacement battery. This affects both stock Android and custom kernels.

### Speed cap
All Codina variants use PRCMU firmware "U8420" that caps CPU to ~800MHz instead of the ~1GHz the SoC supports. Likely a pure software restriction.

### Panel variants
Two LCD panel types exist:
- Samsung LMS380KF01 (WideChips WS2401 controller) — ~90% of units
- Samsung S6D27A1 — ~10% of units
U-Boot stemmy auto-detects via Samsung bootloader's `lcdtype` ATAG parameter.

### USB networking timing
USB networking in pmOS only works if USB is plugged in during the "postmarketOS Loading..." phase. Timing-sensitive.

## Sensors
- STMicroelectronics LIS3DH accelerometer
- Alps HSCDTD008A magnetometer
- Amstaos TMD2672 light and proximity sensor

## Test Device Info
- Serial: 9BA9095C795CD3529C9AB2CB341C39B
- Build: JZO54K.I8160XXMG2 (stock)
- CSC: PHE
- Tested: 2026-03-28 / 2026-03-29
