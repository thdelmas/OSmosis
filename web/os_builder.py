"""OS Builder — assemble custom operating system images.

Supports three build paths:
  1. From base distro (Ubuntu/Debian via debootstrap + preseed, Arch via pacstrap, Alpine)
  2. From scratch (LFS automated pipeline) — future
  3. From template (community profiles) — future

Output formats: raw .img, ISO, rootfs tarball.
"""

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from web.core import Task
from web.ipfs_helpers import (
    ipfs_available as _ipfs_available,
)
from web.ipfs_helpers import (
    layer_cache_key,
    layer_cache_lookup,
    layer_cache_restore,
    layer_cache_save,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUILD_DIR = Path.home() / ".osmosis" / "os-builder"
PROFILES_DIR = BUILD_DIR / "profiles"
OUTPUT_DIR = Path.home() / "Osmosis-downloads" / "os-builds"
PKG_CACHE_DIR = BUILD_DIR / "pkg-cache"


def _collect_layer_cids(profile: "BuildProfile"):
    """Populate profile.layer_cids with CIDs of cached layers used in this build."""
    if not _ipfs_available():
        return
    from web.ipfs_helpers import ipfs_index_load

    base_info = SUPPORTED_BASES.get(profile.base, {})
    suite = profile.suite or base_info.get("default_suite", "")

    index = ipfs_index_load()
    base_key = layer_cache_key("base", distro=profile.base, suite=suite, arch=profile.arch)
    if base_key in index:
        profile.layer_cids["base"] = index[base_key].get("cid", "")

    pkg_key = layer_cache_key(
        "packages",
        distro=profile.base,
        suite=suite,
        arch=profile.arch,
        desktop=profile.desktop,
        packages=sorted(profile.extra_packages),
    )
    if pkg_key in index:
        profile.layer_cids["packages"] = index[pkg_key].get("cid", "")

    cache_key = f"os-pkgcache/{profile.base}-{suite}-{profile.arch}"
    if cache_key in index:
        profile.layer_cids["pkgcache"] = index[cache_key].get("cid", "")


def _restore_pkg_cache(task: Task, distro: str, suite: str, arch: str) -> Path | None:
    """Restore a package cache from IPFS. Returns the cache dir path or None."""
    cache_dir = PKG_CACHE_DIR / f"{distro}-{suite}-{arch}"
    cache_key = f"os-pkgcache/{distro}-{suite}-{arch}"

    if _ipfs_available():
        from web.ipfs_helpers import ipfs_index_load, ipfs_pin_ls

        index = ipfs_index_load()
        entry = index.get(cache_key)
        if entry and entry.get("cid"):
            cid = entry["cid"]
            if ipfs_pin_ls(cid):
                task.emit("Restoring package cache from IPFS...", "info")
                if layer_cache_restore(cid, str(cache_dir), task=task):
                    task.emit("Package cache restored.", "success")
                    return cache_dir

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _save_pkg_cache(task: Task, cache_dir: Path, distro: str, suite: str, arch: str):
    """Pin the package cache directory to IPFS."""
    if not _ipfs_available():
        return
    # Only cache if there are actual files in the directory
    pkg_files = list(cache_dir.glob("*"))
    if len(pkg_files) < 2:
        return

    cache_key = f"os-pkgcache/{distro}-{suite}-{arch}"
    task.emit("Caching package downloads to IPFS...", "info")
    tar_path = cache_dir.parent / f"{distro}-{suite}-{arch}-pkgcache.tar.gz"
    rc = task.run_shell(["tar", "czf", str(tar_path), "-C", str(cache_dir), "."], sudo=True)
    if rc == 0:
        cid = layer_cache_save(
            str(tar_path),
            cache_key,
            {
                "distro": distro,
                "suite": suite,
                "arch": arch,
                "type": "pkgcache",
            },
        )
        if cid:
            task.emit(f"Package cache saved: {cid[:24]}...", "success")
        tar_path.unlink(missing_ok=True)


SUPPORTED_BASES = {
    "ubuntu": {
        "label": "Ubuntu",
        "tool": "debootstrap",
        "suites": ["noble", "jammy", "focal"],
        "default_suite": "noble",
        "mirror": "http://archive.ubuntu.com/ubuntu",
        "arch": ["amd64", "arm64"],
    },
    "debian": {
        "label": "Debian",
        "tool": "debootstrap",
        "suites": ["trixie", "bookworm", "bullseye"],
        "default_suite": "bookworm",
        "mirror": "http://deb.debian.org/debian",
        "arch": ["amd64", "arm64", "armhf", "riscv64"],
    },
    "arch": {
        "label": "Arch Linux",
        "tool": "pacstrap",
        "suites": [],
        "default_suite": "",
        "mirror": "",
        "arch": ["x86_64"],
    },
    "alpine": {
        "label": "Alpine Linux",
        "tool": "apk",
        "suites": ["3.21", "3.20", "3.19"],
        "default_suite": "3.21",
        "mirror": "http://dl-cdn.alpinelinux.org/alpine",
        "arch": ["x86_64", "aarch64", "armv7"],
    },
    "fedora": {
        "label": "Fedora",
        "tool": "dnf",
        "suites": ["41", "40", "39"],
        "default_suite": "41",
        "mirror": "https://download.fedoraproject.org/pub/fedora/linux",
        "arch": ["x86_64", "aarch64"],
    },
    "nixos": {
        "label": "NixOS",
        "tool": "nix",
        "suites": ["24.11", "24.05"],
        "default_suite": "24.11",
        "mirror": "",
        "arch": ["x86_64", "aarch64"],
    },
    "pmos": {
        "label": "postmarketOS",
        "tool": "pmbootstrap",
        "suites": ["v24.12", "v24.06", "edge"],
        "default_suite": "v24.12",
        "mirror": "http://mirror.postmarketos.org/postmarketos/",
        "arch": ["x86_64", "aarch64", "armv7"],
    },
}

INIT_SYSTEMS = ["systemd", "openrc", "sysvinit"]

DESKTOP_ENVIRONMENTS = [
    {"id": "none", "label": "No desktop (server/headless)"},
    {"id": "gnome", "label": "GNOME"},
    {"id": "kde", "label": "KDE Plasma"},
    {"id": "xfce", "label": "Xfce"},
    {"id": "lxqt", "label": "LXQt"},
    {"id": "i3", "label": "i3 (tiling WM)"},
    {"id": "sway", "label": "Sway (Wayland tiling WM)"},
]

OUTPUT_FORMATS = [
    {"id": "img", "label": "Raw disk image (.img)", "desc": "For dd / Osmosis USB writer"},
    {"id": "rootfs", "label": "Root filesystem tarball (.tar.gz)", "desc": "For containers or manual deployment"},
    {"id": "iso", "label": "Bootable ISO (.iso)", "desc": "For burning to DVD or USB"},
]

TARGET_DEVICES = [
    {"id": "generic-x86_64", "label": "Generic PC (x86_64)", "arch": "amd64"},
    {"id": "generic-arm64", "label": "Generic ARM64", "arch": "arm64"},
    {"id": "rpi4", "label": "Raspberry Pi 4/5", "arch": "arm64"},
    {"id": "rpi3", "label": "Raspberry Pi 3", "arch": "arm64"},
    {"id": "rpi-zero2", "label": "Raspberry Pi Zero 2 W", "arch": "arm64"},
    {"id": "vm", "label": "Virtual machine (QEMU/VirtualBox)", "arch": "amd64"},
    {
        "id": "samsung-t03g",
        "label": "Samsung Galaxy Note II (GT-N7100)",
        "arch": "armv7",
        "pmos_device": "samsung-t03g",
        "flash_tool": "heimdall",
        "soc": "exynos4412",
        "kernel": "linux-postmarketos-exynos4",
    },
    {
        "id": "samsung-chagalllte",
        "label": "Samsung Galaxy Tab S 10.5 (SM-T805)",
        "arch": "armv7",
        "pmos_device": "samsung-chagalllte",
        "flash_tool": "heimdall",
        "soc": "exynos5420",
    },
    {
        "id": "samsung-codina",
        "label": "Samsung Galaxy Ace 2 (GT-I8160)",
        "arch": "armv7",
        "pmos_device": "samsung-codina",
        "flash_tool": "heimdall",
        "soc": "u8500",
        "kernel": "linux-postmarketos-stericsson",
        "patches": "patches/samsung-codina",
        "ram_mb": 768,
        "storage_mb": 4096,
    },
]

# ---------------------------------------------------------------------------
# Agent OS templates — pre-configured recipes for agent-first builds
# ---------------------------------------------------------------------------

AGENT_OS_TEMPLATES = {
    "lethe": {
        "id": "lethe",
        "label": "LETHE — Privacy OS with AI guardian",
        "description": (
            "Minimal Linux that boots into a voice-first AI agent interface. "
            "No app store, no home screen — you speak, the agent acts."
        ),
        "repo": "https://github.com/thdelmas/bender.git",
        "defaults": {
            "name": "lethe",
            "base": "pmos",
            "suite": "v24.12",
            "hostname": "lethe",
            "desktop": "none",
            "image_size_mb": 2048,
            "firewall": "nftables",
            "firewall_allow": ["ssh", "8080/tcp"],
            "swap_mb": 256,
            "username": "lethe",
        },
        # Packages per base distro (pmOS uses Alpine apk, Debian uses apt)
        "system_packages_by_base": {
            "pmos": [
                "python3",
                "py3-pip",
                "py3-virtualenv",
                "espeak-ng",
                "ffmpeg",
                "alsa-utils",
                "pulseaudio",
                "chromium",
                "connman",
                "git",
                "curl",
                "sudo",
            ],
            "debian": [
                "python3",
                "python3-pip",
                "python3-venv",
                "espeak",
                "ffmpeg",
                "alsa-utils",
                "pulseaudio",
                "chromium",
                "connman",
                "git",
                "curl",
                "sudo",
            ],
            "alpine": [
                "python3",
                "py3-pip",
                "py3-virtualenv",
                "espeak-ng",
                "ffmpeg",
                "alsa-utils",
                "pulseaudio",
                "chromium",
                "connman",
                "git",
                "curl",
                "sudo",
            ],
        },
        # Fallback for bases not in system_packages_by_base
        "system_packages": [
            "python3",
            "python3-pip",
            "python3-venv",
            "espeak",
            "ffmpeg",
            "alsa-utils",
            "pulseaudio",
            "chromium",
            "connman",
            "git",
            "curl",
            "sudo",
        ],
        # Python packages installed via pip inside a venv
        "pip_packages": [
            "flask",
            "anthropic",
            "openai-whisper",
            "cryptography",
        ],
        # systemd service units to create
        "services": {
            "lethe-agent": {
                "description": "LETHE Agent Server",
                "exec_start": "/opt/lethe/venv/bin/python /opt/lethe/app.py",
                "working_dir": "/opt/lethe",
                "user": "lethe",
                "environment": "HOME=/home/lethe",
                "after": "network-online.target pulseaudio.service",
                "wants": "network-online.target",
                "restart": "always",
            },
            "lethe-kiosk": {
                "description": "LETHE Kiosk Browser",
                "exec_start": (
                    "/usr/bin/chromium --kiosk --no-first-run --disable-translate "
                    "--disable-infobars --noerrdialogs --disable-session-crashed-bubble "
                    "--use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required "
                    "http://localhost:8080"
                ),
                "user": "lethe",
                "environment": "DISPLAY=:0",
                "after": "lethe-agent.service graphical.target",
                "wants": "lethe-agent.service",
                "restart": "on-failure",
                "condition": "display",  # only enabled if device has a display
            },
        },
        # Minimal X/Wayland for kiosk (only if device has a display)
        "kiosk_packages": [
            "xorg",
            "xinit",
            "x11-xserver-utils",
            "openbox",
            "unclutter",
        ],
        # Script that runs inside chroot after everything is installed
        "post_setup": """
# Auto-login on tty1
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << 'AUTOLOGIN'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin lethe --noclear %I $TERM
AUTOLOGIN

# Start X + kiosk on login for display-equipped devices
cat > /home/lethe/.bash_profile << 'PROFILE'
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ] && command -v startx >/dev/null; then
    exec startx /usr/bin/openbox-session
fi
PROFILE

# Openbox autostart launches kiosk browser
mkdir -p /home/lethe/.config/openbox
cat > /home/lethe/.config/openbox/autostart << 'AUTOSTART'
unclutter -idle 0.5 -root &
xset s off -dpms
chromium --kiosk --no-first-run --disable-translate --disable-infobars \
    --noerrdialogs --disable-session-crashed-bubble \
    --use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required \
    http://localhost:8080
AUTOSTART

chown -R lethe:lethe /home/lethe/.bash_profile /home/lethe/.config
""",
    },
}


# ---------------------------------------------------------------------------
# Build profile (serializable config)
# ---------------------------------------------------------------------------


@dataclass
class BuildProfile:
    """Everything needed to reproduce an OS build."""

    name: str = "my-os"
    base: str = "debian"
    suite: str = "bookworm"
    arch: str = "amd64"
    target_device: str = "generic-x86_64"
    output_format: str = "img"
    image_size_mb: int = 4096

    # System
    hostname: str = "osmosis"
    locale: str = "en_US.UTF-8"
    timezone: str = "UTC"
    keyboard_layout: str = "us"
    init_system: str = "systemd"

    # User
    username: str = "user"
    password: str = ""
    ssh_keys: list[str] = field(default_factory=list)
    root_password: str = ""

    # Packages
    extra_packages: list[str] = field(default_factory=list)
    desktop: str = "none"
    extra_repos: list[str] = field(default_factory=list)

    # Disk
    disk_layout: str = "auto"  # auto | lvm | luks
    luks_password: str = ""
    swap_mb: int = 512

    # Network
    network: str = "dhcp"  # dhcp | static
    static_ip: str = ""
    gateway: str = ""
    dns: list[str] = field(default_factory=lambda: ["1.1.1.1", "9.9.9.9"])

    # Post-install
    post_install_script: str = ""

    # Services to enable/disable
    enable_services: list[str] = field(default_factory=list)
    disable_services: list[str] = field(default_factory=list)

    # Firewall
    firewall: str = "none"  # none | ufw | nftables
    firewall_allow: list[str] = field(default_factory=lambda: ["ssh"])

    # Agent OS template (e.g. "lethe") — applies an overlay after base config
    agent_template: str = ""

    # IPFS layer CIDs (populated after build for reproducibility)
    layer_cids: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @classmethod
    def from_dict(cls, d: dict) -> "BuildProfile":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})

    def save(self, path: Path | None = None) -> Path:
        if path is None:
            PROFILES_DIR.mkdir(parents=True, exist_ok=True)
            path = PROFILES_DIR / f"{self.name}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path

    @classmethod
    def load(cls, path: Path) -> "BuildProfile":
        return cls.from_dict(json.loads(path.read_text()))


# ---------------------------------------------------------------------------
# Preseed / answer file generators
# ---------------------------------------------------------------------------


def generate_preseed(profile: BuildProfile) -> str:
    """Generate a Debian/Ubuntu preseed file from the profile."""
    lines = [
        "# Osmosis auto-generated preseed",
        f"d-i debian-installer/locale string {profile.locale}",
        f"d-i keyboard-configuration/xkb-keymap select {profile.keyboard_layout}",
        f"d-i time/zone string {profile.timezone}",
        f"d-i netcfg/hostname string {profile.hostname}",
        "d-i netcfg/choose_interface select auto",
    ]

    if profile.network == "dhcp":
        lines.append("d-i netcfg/get_hostname string unassigned-hostname")
    else:
        lines.extend(
            [
                f"d-i netcfg/get_ipaddress string {profile.static_ip}",
                f"d-i netcfg/get_gateway string {profile.gateway}",
                f"d-i netcfg/get_nameservers string {' '.join(profile.dns)}",
            ]
        )

    # Disk
    if profile.disk_layout == "auto":
        lines.extend(
            [
                "d-i partman-auto/method string regular",
                "d-i partman-auto/choose_recipe select atomic",
                "d-i partman/confirm boolean true",
                "d-i partman/confirm_nooverwrite boolean true",
            ]
        )
    elif profile.disk_layout == "lvm":
        lines.extend(
            [
                "d-i partman-auto/method string lvm",
                "d-i partman-lvm/confirm boolean true",
                "d-i partman-lvm/device_remove_lvm boolean true",
            ]
        )
    elif profile.disk_layout == "luks":
        lines.extend(
            [
                "d-i partman-auto/method string crypto",
                "d-i partman-crypto/passphrase string placeholder",
                "d-i partman-crypto/passphrase-again string placeholder",
            ]
        )

    # User
    lines.extend(
        [
            f"d-i passwd/username string {profile.username}",
            "d-i passwd/user-password-crypted string !",
            "d-i user-setup/allow-password-weak boolean true",
        ]
    )

    if profile.root_password:
        lines.append("d-i passwd/root-login boolean true")
    else:
        lines.append("d-i passwd/root-login boolean false")

    # Packages
    pkg_list = list(profile.extra_packages)
    if profile.firewall == "ufw":
        pkg_list.append("ufw")
    elif profile.firewall == "nftables":
        pkg_list.append("nftables")
    if profile.ssh_keys:
        pkg_list.append("openssh-server")
    if pkg_list:
        lines.append(f"d-i pkgsel/include string {' '.join(pkg_list)}")

    lines.append("d-i finish-install/reboot_in_progress note")
    return "\n".join(lines) + "\n"


def generate_alpine_answers(profile: BuildProfile) -> str:
    """Generate an Alpine Linux setup-alpine answer file."""
    lines = [
        f'KEYMAPOPTS="{profile.keyboard_layout} {profile.keyboard_layout}"',
        f'HOSTNAMEOPTS="-n {profile.hostname}"',
        'INTERFACESOPTS="auto lo',
        "iface lo inet loopback",
        "",
        "auto eth0",
    ]
    if profile.network == "dhcp":
        lines.append('iface eth0 inet dhcp"')
    else:
        lines.extend(
            [
                "iface eth0 inet static",
                f"    address {profile.static_ip}",
                f'    gateway {profile.gateway}"',
            ]
        )

    lines.extend(
        [
            'DNSOPTS="-d example.com ' + " ".join(profile.dns) + '"',
            f'TIMEZONEOPTS="-z {profile.timezone}"',
            'PROXYOPTS="none"',
            'APKREPOSOPTS="-1"',
            'SSHDOPTS="-c openssh"',
            'NTPOPTS="-c chrony"',
            'DISKOPTS="-m sys /dev/sda"',
        ]
    )
    return "\n".join(lines) + "\n"


def generate_pacstrap_script(profile: BuildProfile) -> str:
    """Generate an Arch Linux installation script using pacstrap."""
    pkgs = ["base", "linux", "linux-firmware"]
    if profile.init_system == "systemd":
        pkgs.append("systemd")

    if profile.desktop == "gnome":
        pkgs.extend(["gnome", "gnome-extra", "gdm"])
    elif profile.desktop == "kde":
        pkgs.extend(["plasma-meta", "kde-applications-meta", "sddm"])
    elif profile.desktop == "xfce":
        pkgs.extend(["xfce4", "xfce4-goodies", "lightdm", "lightdm-gtk-greeter"])
    elif profile.desktop == "lxqt":
        pkgs.extend(["lxqt", "sddm"])
    elif profile.desktop == "i3":
        pkgs.extend(["i3-wm", "i3status", "dmenu", "xorg-server", "xorg-xinit"])
    elif profile.desktop == "sway":
        pkgs.extend(["sway", "swaybar", "swayidle", "swaylock", "foot", "wmenu"])

    pkgs.extend(profile.extra_packages)

    lines = [
        "#!/bin/bash",
        "set -euo pipefail",
        "",
        "# Osmosis auto-generated Arch Linux install script",
        f'HOSTNAME="{profile.hostname}"',
        f'USERNAME="{profile.username}"',
        f'LOCALE="{profile.locale}"',
        f'TIMEZONE="{profile.timezone}"',
        f'KEYMAP="{profile.keyboard_layout}"',
        "",
        "MOUNT=/mnt",
        "",
        f"pacstrap $MOUNT {' '.join(pkgs)}",
        "genfstab -U $MOUNT >> $MOUNT/etc/fstab",
        "",
        "# Configure inside chroot",
        "arch-chroot $MOUNT /bin/bash <<'CHROOT'",
        "set -euo pipefail",
        f"ln -sf /usr/share/zoneinfo/{profile.timezone} /etc/localtime",
        "hwclock --systohc",
        f'echo "{profile.locale} UTF-8" >> /etc/locale.gen',
        "locale-gen",
        f'echo "LANG={profile.locale}" > /etc/locale.conf',
        f'echo "KEYMAP={profile.keyboard_layout}" > /etc/vconsole.conf',
        f'echo "{profile.hostname}" > /etc/hostname',
        "",
        f"useradd -m -G wheel -s /bin/bash {profile.username}",
        "echo '%wheel ALL=(ALL:ALL) ALL' >> /etc/sudoers",
        "",
        "# Install bootloader",
        "pacman -S --noconfirm grub efibootmgr",
        "grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=GRUB",
        "grub-mkconfig -o /boot/grub/grub.cfg",
    ]

    if profile.firewall == "ufw":
        lines.extend(
            [
                "pacman -S --noconfirm ufw",
                "systemctl enable ufw",
                *[f"ufw allow {svc}" for svc in profile.firewall_allow],
                "ufw --force enable",
            ]
        )

    for svc in profile.enable_services:
        lines.append(f"systemctl enable {svc}")
    for svc in profile.disable_services:
        lines.append(f"systemctl disable {svc}")

    lines.extend(["CHROOT", ""])

    if profile.post_install_script:
        lines.extend(
            [
                "# User post-install script",
                "arch-chroot $MOUNT /bin/bash <<'POSTSCRIPT'",
                profile.post_install_script,
                "POSTSCRIPT",
                "",
            ]
        )

    return "\n".join(lines) + "\n"


def generate_kickstart(profile: BuildProfile) -> str:
    """Generate a Fedora Kickstart file from the profile."""
    lines = [
        "# Osmosis auto-generated Kickstart",
        "lang " + profile.locale,
        "keyboard " + profile.keyboard_layout,
        "timezone " + profile.timezone,
        "rootpw --lock",
    ]

    # Network
    if profile.network == "dhcp":
        lines.append("network --bootproto=dhcp --device=link --activate --hostname=" + profile.hostname)
    else:
        dns_str = ",".join(profile.dns)
        lines.append(
            f"network --bootproto=static --ip={profile.static_ip} "
            f"--gateway={profile.gateway} --nameserver={dns_str} "
            f"--device=link --activate --hostname={profile.hostname}"
        )

    # Disk
    if profile.disk_layout == "auto":
        lines.extend(
            [
                "clearpart --all --initlabel",
                "autopart --type=plain",
            ]
        )
    elif profile.disk_layout == "lvm":
        lines.extend(
            [
                "clearpart --all --initlabel",
                "autopart --type=lvm",
            ]
        )
    elif profile.disk_layout == "luks":
        lines.extend(
            [
                "clearpart --all --initlabel",
                "autopart --type=lvm --encrypted",
            ]
        )

    lines.append("bootloader --location=mbr")

    # User
    lines.append(f"user --name={profile.username} --groups=wheel --shell=/bin/bash")
    if profile.password:
        lines.append(f"user --name={profile.username} --password={profile.password} --plaintext")

    # SELinux and firewall
    lines.append("selinux --enforcing")
    if profile.firewall == "none":
        lines.append("firewall --disabled")
    else:
        allow = " ".join(f"--service={svc}" for svc in profile.firewall_allow)
        lines.append(f"firewall --enabled {allow}")

    # Packages
    lines.append("")
    lines.append("%packages")
    lines.append("@core")

    if profile.desktop == "gnome":
        lines.append("@gnome-desktop")
    elif profile.desktop == "kde":
        lines.append("@kde-desktop")
    elif profile.desktop == "xfce":
        lines.append("@xfce-desktop")
    elif profile.desktop == "lxqt":
        lines.append("@lxqt-desktop")
    elif profile.desktop == "i3":
        lines.extend(["i3", "i3status", "dmenu", "xorg-x11-server-Xorg"])
    elif profile.desktop == "sway":
        lines.extend(["sway", "swayidle", "swaylock", "foot", "wmenu"])

    for pkg in profile.extra_packages:
        lines.append(pkg)

    if profile.firewall == "ufw":
        lines.append("ufw")
    elif profile.firewall == "nftables":
        lines.append("nftables")

    if profile.ssh_keys:
        lines.append("openssh-server")

    lines.append("%end")

    # Post-install
    if profile.post_install_script or profile.ssh_keys:
        lines.append("")
        lines.append("%post")
        if profile.ssh_keys:
            lines.append(f"mkdir -p /home/{profile.username}/.ssh")
            lines.append(f"chmod 700 /home/{profile.username}/.ssh")
            for key in profile.ssh_keys:
                lines.append(f"echo '{key}' >> /home/{profile.username}/.ssh/authorized_keys")
            lines.append(f"chmod 600 /home/{profile.username}/.ssh/authorized_keys")
            lines.append(f"chown -R {profile.username}:{profile.username} /home/{profile.username}/.ssh")
        if profile.post_install_script:
            lines.append(profile.post_install_script)
        lines.append("%end")

    return "\n".join(lines) + "\n"


def generate_nix_config(profile: BuildProfile) -> str:
    """Generate a NixOS configuration.nix from the profile."""
    # Build the extra packages list for environment.systemPackages
    sys_pkgs = []
    for pkg in profile.extra_packages:
        sys_pkgs.append(f"      pkgs.{pkg}")

    # Desktop
    desktop_lines = []
    if profile.desktop == "gnome":
        desktop_lines = [
            "  services.xserver.enable = true;",
            "  services.xserver.displayManager.gdm.enable = true;",
            "  services.xserver.desktopManager.gnome.enable = true;",
        ]
    elif profile.desktop == "kde":
        desktop_lines = [
            "  services.xserver.enable = true;",
            "  services.displayManager.sddm.enable = true;",
            "  services.xserver.desktopManager.plasma5.enable = true;",
        ]
    elif profile.desktop == "xfce":
        desktop_lines = [
            "  services.xserver.enable = true;",
            "  services.xserver.desktopManager.xfce.enable = true;",
        ]
    elif profile.desktop == "i3":
        desktop_lines = [
            "  services.xserver.enable = true;",
            "  services.xserver.windowManager.i3.enable = true;",
        ]
    elif profile.desktop == "sway":
        desktop_lines = [
            "  programs.sway.enable = true;",
        ]

    # Firewall
    if profile.firewall != "none":
        fw_lines = [
            "  networking.firewall.enable = true;",
            "  networking.firewall.allowedTCPPorts = [ "
            + " ".join("22" if svc == "ssh" else svc for svc in profile.firewall_allow)
            + " ];",
        ]
    else:
        fw_lines = ["  networking.firewall.enable = false;"]

    # Network
    if profile.network == "dhcp":
        net_lines = ["  networking.useDHCP = true;"]
    else:
        net_lines = [
            "  networking.useDHCP = false;",
            "  networking.interfaces.eth0.ipv4.addresses = [ {",
            f'    address = "{profile.static_ip.split("/")[0]}";',
            f"    prefixLength = {profile.static_ip.split('/')[-1] if '/' in profile.static_ip else '24'};",
            "  } ];",
            f'  networking.defaultGateway = "{profile.gateway}";',
            "  networking.nameservers = [ {} ];".format(" ".join(f'"{d}"' for d in profile.dns)),
        ]

    # SSH
    ssh_lines = []
    if profile.ssh_keys:
        ssh_lines = [
            "  services.openssh.enable = true;",
            f"  users.users.{profile.username}.openssh.authorizedKeys.keys = [",
        ]
        for key in profile.ssh_keys:
            ssh_lines.append(f'    "{key}"')
        ssh_lines.append("  ];")

    lines = [
        "# Osmosis auto-generated NixOS configuration",
        "{ config, pkgs, ... }:",
        "",
        "{",
        "  imports = [",
        "    ./hardware-configuration.nix",
        "  ];",
        "",
        "  boot.loader.systemd-boot.enable = true;",
        "  boot.loader.efi.canTouchEfiVariables = true;",
        "",
        f'  networking.hostName = "{profile.hostname}";',
        *net_lines,
        "",
        f'  time.timeZone = "{profile.timezone}";',
        f'  i18n.defaultLocale = "{profile.locale}";',
        f'  console.keyMap = "{profile.keyboard_layout}";',
        "",
        *desktop_lines,
        "",
        *fw_lines,
        "",
        *ssh_lines,
        "",
        f"  users.users.{profile.username} = {{",
        "    isNormalUser = true;",
        '    extraGroups = [ "wheel" "networkmanager" ];',
        "  };",
        "",
        "  environment.systemPackages = with pkgs; [",
        *sys_pkgs,
        "  ];",
        "",
        f'  system.stateVersion = "{profile.suite}";',
        "}",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Build engine
# ---------------------------------------------------------------------------


def _check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def _desktop_packages_deb(desktop: str) -> list[str]:
    """Return apt package list for a desktop environment."""
    mapping = {
        "gnome": ["ubuntu-desktop-minimal"] if True else ["task-gnome-desktop"],
        "kde": ["kde-plasma-desktop", "sddm"],
        "xfce": ["xfce4", "xfce4-goodies", "lightdm"],
        "lxqt": ["lxqt", "sddm"],
        "i3": ["i3", "i3status", "dmenu", "xorg"],
        "sway": ["sway", "swayidle", "swaylock", "foot", "wmenu"],
    }
    return mapping.get(desktop, [])


def _agent_overlay_packages(template_id: str, base: str = "") -> list[str]:
    """Return system packages required by an agent OS template for the given base."""
    tmpl = AGENT_OS_TEMPLATES.get(template_id)
    if not tmpl:
        return []
    by_base = tmpl.get("system_packages_by_base", {})
    if base and base in by_base:
        return list(by_base[base])
    return list(tmpl.get("system_packages", []))


def _agent_overlay_kiosk_packages(template_id: str) -> list[str]:
    """Return kiosk display packages for an agent OS template."""
    tmpl = AGENT_OS_TEMPLATES.get(template_id)
    if not tmpl:
        return []
    return list(tmpl.get("kiosk_packages", []))


def _apply_agent_overlay(task: Task, profile: BuildProfile, rootfs: Path):
    """Apply an agent OS template overlay inside a configured rootfs.

    This runs after the base system is configured and packages are installed.
    It clones the agent repo, creates a venv, installs pip packages,
    writes systemd services, and runs the template's post_setup script.
    """
    tmpl = AGENT_OS_TEMPLATES.get(profile.agent_template)
    if not tmpl:
        return

    def chroot_run(cmd: list[str]) -> int:
        return task.run_shell(["chroot", str(rootfs)] + cmd, sudo=True)

    template_id = tmpl["id"]
    task.emit("")
    task.emit(f"Applying agent overlay: {tmpl['label']}", "info")

    # Step 1: Clone the agent repo into /opt/<template_id>
    repo_url = tmpl.get("repo", "")
    install_dir = f"/opt/{template_id}"
    if repo_url:
        task.emit(f"Cloning {repo_url} into {install_dir}...")
        chroot_run(["git", "clone", "--depth=1", repo_url, install_dir])
    else:
        chroot_run(["mkdir", "-p", install_dir])

    # Step 2: Create Python venv and install pip packages
    pip_packages = tmpl.get("pip_packages", [])
    if pip_packages:
        task.emit("Creating Python virtual environment...")
        chroot_run(["python3", "-m", "venv", f"{install_dir}/venv"])
        task.emit(f"Installing pip packages: {', '.join(pip_packages)}")
        chroot_run(
            [
                f"{install_dir}/venv/bin/pip",
                "install",
                "--no-cache-dir",
                *pip_packages,
            ]
        )

    # Step 3: Create systemd service units
    services = tmpl.get("services", {})
    for svc_name, svc_cfg in services.items():
        # Skip display-conditional services if desktop is none and no kiosk packages
        if svc_cfg.get("condition") == "display" and profile.desktop == "none":
            task.emit(f"Skipping {svc_name}.service (no display configured)")
            continue

        task.emit(f"Creating {svc_name}.service...")
        unit = f"[Unit]\nDescription={svc_cfg['description']}\nAfter={svc_cfg.get('after', 'network-online.target')}\n"
        if svc_cfg.get("wants"):
            unit += f"Wants={svc_cfg['wants']}\n"
        unit += (
            f"\n[Service]\n"
            f"Type=simple\n"
            f"ExecStart={svc_cfg['exec_start']}\n"
            f"Restart={svc_cfg.get('restart', 'always')}\n"
            f"RestartSec=3\n"
        )
        if svc_cfg.get("working_dir"):
            unit += f"WorkingDirectory={svc_cfg['working_dir']}\n"
        if svc_cfg.get("user"):
            unit += f"User={svc_cfg['user']}\n"
        if svc_cfg.get("environment"):
            unit += f"Environment={svc_cfg['environment']}\n"
        unit += "\n[Install]\nWantedBy=multi-user.target\n"

        svc_path = rootfs / "etc" / "systemd" / "system" / f"{svc_name}.service"
        task.run_shell(["bash", "-c", f"cat > {svc_path} << 'SVCEOF'\n{unit}SVCEOF"], sudo=True)
        chroot_run(["systemctl", "enable", svc_name])

    # Step 4: Run template post-setup script
    post_setup = tmpl.get("post_setup", "").strip()
    if post_setup:
        task.emit("Running agent post-setup script...")
        script_path = "/tmp/agent-post-setup.sh"
        task.run_shell(
            [
                "bash",
                "-c",
                f"cat > {rootfs}{script_path} << 'AGENTEOF'\n#!/bin/bash\nset -euo pipefail\n{post_setup}\nAGENTEOF",
            ],
            sudo=True,
        )
        chroot_run(["chmod", "+x", script_path])
        chroot_run(["bash", script_path])

    # Step 5: Set ownership
    chroot_run(["chown", "-R", f"{profile.username}:{profile.username}", install_dir])

    task.emit(f"Agent overlay '{template_id}' applied.", "success")


def _apply_template_defaults(profile: BuildProfile):
    """Merge agent OS template defaults into the profile (profile values take priority)."""
    tmpl = AGENT_OS_TEMPLATES.get(profile.agent_template)
    if not tmpl:
        return
    defaults = tmpl.get("defaults", {})
    for key, val in defaults.items():
        # Only apply if the profile still has the dataclass default
        field_obj = BuildProfile.__dataclass_fields__.get(key)
        if field_obj is None:
            continue
        current = getattr(profile, key)
        # Apply template default if the field is at its original default
        if current == field_obj.default or (
            callable(getattr(field_obj, "default_factory", None)) and current == field_obj.default_factory()
        ):
            setattr(profile, key, val)

    # Inject agent system packages into extra_packages (dedup)
    agent_pkgs = _agent_overlay_packages(profile.agent_template)
    kiosk_pkgs = _agent_overlay_kiosk_packages(profile.agent_template)
    existing = set(profile.extra_packages)
    for pkg in agent_pkgs + kiosk_pkgs:
        if pkg not in existing:
            profile.extra_packages.append(pkg)
            existing.add(pkg)


def build_os(task: Task, profile: BuildProfile):
    """Main build entry point — runs in a background Task thread."""

    # Apply agent OS template defaults before building
    if profile.agent_template:
        tmpl = AGENT_OS_TEMPLATES.get(profile.agent_template)
        if not tmpl:
            task.emit(f"Unknown agent template: {profile.agent_template}", "error")
            task.done(False)
            return
        _apply_template_defaults(profile)
        task.emit(f"Agent template: {tmpl['label']}", "info")

    task.emit(f"Build profile: {profile.name}", "info")
    task.emit(f"Base: {profile.base} {profile.suite} ({profile.arch})", "info")
    task.emit(f"Target: {profile.target_device}", "info")
    task.emit(f"Output: {profile.output_format}", "info")
    task.emit("")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    if profile.base in ("ubuntu", "debian"):
        _build_debootstrap(task, profile)
    elif profile.base == "arch":
        _build_arch(task, profile)
    elif profile.base == "alpine":
        _build_alpine(task, profile)
    elif profile.base == "fedora":
        _build_fedora(task, profile)
    elif profile.base == "nixos":
        _build_nixos(task, profile)
    elif profile.base == "pmos":
        _build_pmos(task, profile)
    else:
        task.emit(f"Unsupported base: {profile.base}", "error")
        task.done(False)


def _build_debootstrap(task: Task, profile: BuildProfile):
    """Build a Debian/Ubuntu image using debootstrap."""

    if not _check_tool("debootstrap"):
        task.emit("debootstrap is not installed. Install it with: sudo apt install debootstrap", "error")
        task.done(False)
        return

    work_dir = Path(tempfile.mkdtemp(prefix="osmosis-build-", dir=str(BUILD_DIR)))
    rootfs = work_dir / "rootfs"
    rootfs.mkdir()

    try:
        # Step 1: debootstrap (with IPFS layer caching)
        base_info = SUPPORTED_BASES[profile.base]
        suite = profile.suite or base_info["default_suite"]
        mirror = base_info["mirror"]

        base_cache = layer_cache_key("base", distro=profile.base, suite=suite, arch=profile.arch)
        base_restored = False

        if _ipfs_available():
            cached_cid = layer_cache_lookup(base_cache)
            if cached_cid:
                task.emit(f"Restoring base layer from IPFS cache: {cached_cid[:24]}...", "info")
                base_restored = layer_cache_restore(cached_cid, str(rootfs), task=task)
                if base_restored:
                    task.emit("Base layer restored from cache.", "success")

        if not base_restored:
            task.emit(f"Running debootstrap for {profile.base} {suite} ({profile.arch})...", "info")
            task.emit("This may take several minutes depending on your connection.", "info")
            task.emit("")

            debootstrap_cmd = [
                "debootstrap",
                "--arch",
                profile.arch,
                "--variant=minbase",
                suite,
                str(rootfs),
                mirror,
            ]
            rc = task.run_shell(debootstrap_cmd, sudo=True)
            if rc != 0:
                task.emit("debootstrap failed.", "error")
                task.done(False)
                return

            # Cache the base layer to IPFS
            if _ipfs_available():
                task.emit("Caching base layer to IPFS...", "info")
                base_tar = work_dir / "base-layer.tar.gz"
                rc_tar = task.run_shell(["tar", "czf", str(base_tar), "-C", str(rootfs), "."], sudo=True)
                if rc_tar == 0:
                    cid = layer_cache_save(
                        str(base_tar), base_cache, {"distro": profile.base, "suite": suite, "arch": profile.arch}
                    )
                    if cid:
                        task.emit(f"Base layer cached: {cid[:24]}...", "success")
                    base_tar.unlink(missing_ok=True)

        task.emit("")
        task.emit("Base system installed. Configuring...", "info")

        # Step 2: Configure the system inside chroot
        _configure_debootstrap_rootfs(task, profile, rootfs)

        # Step 3: Generate preseed for reference
        preseed = generate_preseed(profile)
        preseed_path = work_dir / "preseed.cfg"
        preseed_path.write_text(preseed)
        task.emit(f"Preseed saved to {preseed_path}", "info")

        # Step 4: Package output
        _collect_layer_cids(profile)
        _package_output(task, profile, rootfs, work_dir)

    except Exception as e:
        task.emit(f"Build failed: {e}", "error")
        task.done(False)
    finally:
        # Clean up rootfs (needs sudo because debootstrap creates root-owned files)
        task.emit("Cleaning up build directory...", "info")
        task.run_shell(["rm", "-rf", str(work_dir)], sudo=True)


def _configure_debootstrap_rootfs(task: Task, profile: BuildProfile, rootfs: Path):
    """Configure a debootstrapped rootfs via chroot."""

    def chroot_run(cmd: list[str]) -> int:
        return task.run_shell(["chroot", str(rootfs)] + cmd, sudo=True)

    # Mount virtual filesystems
    for fs, tgt in [("proc", "proc"), ("sysfs", "sys"), ("devtmpfs", "dev")]:
        task.run_shell(["mount", "-t", fs, fs, str(rootfs / tgt)], sudo=True)
    task.run_shell(["mount", "--bind", "/dev/pts", str(rootfs / "dev" / "pts")], sudo=True)

    try:
        # Hostname
        task.emit(f"Setting hostname: {profile.hostname}")
        task.run_shell(["bash", "-c", f"echo '{profile.hostname}' > {rootfs}/etc/hostname"], sudo=True)

        hosts = f"127.0.0.1\tlocalhost\n127.0.1.1\t{profile.hostname}\n"
        task.run_shell(["bash", "-c", f"echo '{hosts}' > {rootfs}/etc/hosts"], sudo=True)

        # Locale & timezone
        task.emit(f"Setting locale: {profile.locale}")
        chroot_run(["bash", "-c", f"echo '{profile.locale} UTF-8' > /etc/locale.gen"])
        chroot_run(["locale-gen"])
        chroot_run(["bash", "-c", f"echo 'LANG={profile.locale}' > /etc/locale.conf"])

        task.emit(f"Setting timezone: {profile.timezone}")
        chroot_run(["ln", "-sf", f"/usr/share/zoneinfo/{profile.timezone}", "/etc/localtime"])

        # Keyboard
        chroot_run(["bash", "-c", f"echo 'KEYMAP={profile.keyboard_layout}' > /etc/vconsole.conf"])

        # Create user
        task.emit(f"Creating user: {profile.username}")
        chroot_run(["useradd", "-m", "-s", "/bin/bash", "-G", "sudo", profile.username])

        if profile.password:
            chroot_run(["bash", "-c", f"echo '{profile.username}:{profile.password}' | chpasswd"])

        if profile.root_password:
            chroot_run(["bash", "-c", f"echo 'root:{profile.root_password}' | chpasswd"])

        # SSH keys
        if profile.ssh_keys:
            task.emit("Installing SSH keys...")
            ssh_dir = f"/home/{profile.username}/.ssh"
            chroot_run(["mkdir", "-p", ssh_dir])
            authorized = "\n".join(profile.ssh_keys) + "\n"
            chroot_run(["bash", "-c", f"echo '{authorized}' > {ssh_dir}/authorized_keys"])
            chroot_run(["chmod", "700", ssh_dir])
            chroot_run(["chmod", "600", f"{ssh_dir}/authorized_keys"])
            chroot_run(["chown", "-R", f"{profile.username}:{profile.username}", ssh_dir])

        # Install extra packages
        all_pkgs = list(profile.extra_packages)
        de_pkgs = _desktop_packages_deb(profile.desktop)
        all_pkgs.extend(de_pkgs)

        if profile.firewall == "ufw":
            all_pkgs.append("ufw")
        elif profile.firewall == "nftables":
            all_pkgs.append("nftables")

        if profile.ssh_keys:
            all_pkgs.append("openssh-server")

        # Install kernel
        if profile.base == "ubuntu":
            all_pkgs.append("linux-generic")
        else:
            all_pkgs.append("linux-image-" + profile.arch)

        # Bootloader
        all_pkgs.extend(["grub-pc", "grub-efi-amd64-bin"] if profile.arch == "amd64" else ["grub-efi-arm64"])

        if all_pkgs:
            # Check for package layer cache
            base_info = SUPPORTED_BASES[profile.base]
            suite = profile.suite or base_info["default_suite"]
            pkg_cache = layer_cache_key(
                "packages",
                distro=profile.base,
                suite=suite,
                arch=profile.arch,
                desktop=profile.desktop,
                packages=all_pkgs,
            )
            pkg_restored = False

            if _ipfs_available():
                cached_cid = layer_cache_lookup(pkg_cache)
                if cached_cid:
                    task.emit("Restoring package layer from IPFS cache...", "info")
                    # Unmount before restoring over rootfs
                    for mnt in ["dev/pts", "dev", "proc", "sys"]:
                        task.run_shell(["umount", "-lf", str(rootfs / mnt)], sudo=True)
                    # Clear rootfs and restore from cache
                    task.run_shell(["rm", "-rf", str(rootfs)], sudo=True)
                    rootfs.mkdir()
                    pkg_restored = layer_cache_restore(cached_cid, str(rootfs), task=task)
                    # Re-mount virtual filesystems
                    for fs, tgt in [("proc", "proc"), ("sysfs", "sys"), ("devtmpfs", "dev")]:
                        task.run_shell(["mount", "-t", fs, fs, str(rootfs / tgt)], sudo=True)
                    task.run_shell(["mount", "--bind", "/dev/pts", str(rootfs / "dev" / "pts")], sudo=True)
                    if pkg_restored:
                        task.emit("Package layer restored from cache.", "success")

            if not pkg_restored:
                # Restore package download cache to avoid re-downloading .debs
                pkg_cache_dir = _restore_pkg_cache(task, profile.base, suite, profile.arch)
                apt_cache = rootfs / "var" / "cache" / "apt" / "archives"
                apt_cache.mkdir(parents=True, exist_ok=True)
                if pkg_cache_dir and pkg_cache_dir.exists():
                    task.run_shell(["mount", "--bind", str(pkg_cache_dir), str(apt_cache)], sudo=True)

                task.emit(f"Installing packages: {', '.join(all_pkgs[:10])}{'...' if len(all_pkgs) > 10 else ''}")
                chroot_run(["bash", "-c", "apt-get update -qq"])
                chroot_run(
                    [
                        "bash",
                        "-c",
                        "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "
                        + " ".join(all_pkgs),
                    ]
                )

                # Save package cache, then unmount
                if pkg_cache_dir:
                    _save_pkg_cache(task, pkg_cache_dir, profile.base, suite, profile.arch)
                    task.run_shell(["umount", "-lf", str(apt_cache)], sudo=True)

                # Cache the package layer
                if _ipfs_available():
                    task.emit("Caching package layer to IPFS...", "info")
                    # Unmount before tarring
                    for mnt in ["dev/pts", "dev", "proc", "sys"]:
                        task.run_shell(["umount", "-lf", str(rootfs / mnt)], sudo=True)
                    pkg_tar = rootfs.parent / "pkg-layer.tar.gz"
                    rc_tar = task.run_shell(["tar", "czf", str(pkg_tar), "-C", str(rootfs), "."], sudo=True)
                    # Re-mount
                    for fs, tgt in [("proc", "proc"), ("sysfs", "sys"), ("devtmpfs", "dev")]:
                        task.run_shell(["mount", "-t", fs, fs, str(rootfs / tgt)], sudo=True)
                    task.run_shell(["mount", "--bind", "/dev/pts", str(rootfs / "dev" / "pts")], sudo=True)
                    if rc_tar == 0:
                        cid = layer_cache_save(
                            str(pkg_tar),
                            pkg_cache,
                            {
                                "distro": profile.base,
                                "suite": suite,
                                "arch": profile.arch,
                                "desktop": profile.desktop,
                                "package_count": len(all_pkgs),
                            },
                        )
                        if cid:
                            task.emit(f"Package layer cached: {cid[:24]}...", "success")
                        pkg_tar.unlink(missing_ok=True)

        # Enable/disable services
        for svc in profile.enable_services:
            chroot_run(["systemctl", "enable", svc])
        for svc in profile.disable_services:
            chroot_run(["systemctl", "disable", svc])

        # Firewall
        if profile.firewall == "ufw":
            task.emit("Configuring UFW firewall...")
            for allow in profile.firewall_allow:
                chroot_run(["ufw", "allow", allow])
            chroot_run(["ufw", "--force", "enable"])

        # Network
        if profile.network == "dhcp":
            netcfg = "[Match]\nName=en*\n\n[Network]\nDHCP=yes\n"
        else:
            netcfg = (
                f"[Match]\nName=en*\n\n[Network]\n"
                f"Address={profile.static_ip}\n"
                f"Gateway={profile.gateway}\n" + "".join(f"DNS={d}\n" for d in profile.dns)
            )
        chroot_run(["mkdir", "-p", "/etc/systemd/network"])
        chroot_run(["bash", "-c", f"cat > /etc/systemd/network/20-wired.network << 'NETEOF'\n{netcfg}NETEOF"])
        chroot_run(["systemctl", "enable", "systemd-networkd"])

        # Post-install script
        if profile.post_install_script:
            task.emit("Running post-install script...")
            script_path = "/tmp/osmosis-post-install.sh"
            task.run_shell(
                ["bash", "-c", f"cat > {rootfs}{script_path} << 'SCRIPTEOF'\n{profile.post_install_script}\nSCRIPTEOF"],
                sudo=True,
            )
            chroot_run(["chmod", "+x", script_path])
            chroot_run(["bash", script_path])

        # Agent OS overlay (LETHE, etc.) — runs after base config
        if profile.agent_template:
            _apply_agent_overlay(task, profile, rootfs)

        task.emit("System configuration complete.", "success")

    finally:
        # Unmount virtual filesystems
        for mnt in ["dev/pts", "dev", "proc", "sys"]:
            task.run_shell(["umount", "-lf", str(rootfs / mnt)], sudo=True)


def _build_arch(task: Task, profile: BuildProfile):
    """Build an Arch Linux image using pacstrap."""

    if not _check_tool("pacstrap"):
        task.emit("pacstrap is not installed. Install arch-install-scripts.", "error")
        task.done(False)
        return

    work_dir = Path(tempfile.mkdtemp(prefix="osmosis-build-", dir=str(BUILD_DIR)))
    rootfs = work_dir / "rootfs"
    rootfs.mkdir()

    try:
        task.emit("Generating Arch Linux install script...", "info")
        script = generate_pacstrap_script(profile)
        script_path = work_dir / "install.sh"
        script_path.write_text(script)
        task.emit(f"Install script saved to {script_path}", "info")

        base_cache = layer_cache_key("base", distro="arch", suite="rolling", arch=profile.arch)
        base_restored = False

        if _ipfs_available():
            cached_cid = layer_cache_lookup(base_cache)
            if cached_cid:
                task.emit(f"Restoring base layer from IPFS cache: {cached_cid[:24]}...", "info")
                base_restored = layer_cache_restore(cached_cid, str(rootfs), task=task)
                if base_restored:
                    task.emit("Base layer restored from cache.", "success")

        if not base_restored:
            task.emit("Running pacstrap...", "info")
            pkgs = ["base", "linux", "linux-firmware"]
            rc = task.run_shell(["pacstrap", str(rootfs)] + pkgs, sudo=True)
            if rc != 0:
                task.emit("pacstrap failed.", "error")
                task.done(False)
                return

            if _ipfs_available():
                task.emit("Caching base layer to IPFS...", "info")
                base_tar = work_dir / "base-layer.tar.gz"
                rc_tar = task.run_shell(["tar", "czf", str(base_tar), "-C", str(rootfs), "."], sudo=True)
                if rc_tar == 0:
                    cid = layer_cache_save(str(base_tar), base_cache, {"distro": "arch", "arch": profile.arch})
                    if cid:
                        task.emit(f"Base layer cached: {cid[:24]}...", "success")
                    base_tar.unlink(missing_ok=True)

        # Generate fstab
        task.run_shell(["bash", "-c", f"genfstab -U {rootfs} >> {rootfs}/etc/fstab"], sudo=True)

        # Configure via chroot
        task.emit("Configuring Arch system...", "info")
        _configure_arch_chroot(task, profile, rootfs)

        _collect_layer_cids(profile)
        _package_output(task, profile, rootfs, work_dir)

    except Exception as e:
        task.emit(f"Build failed: {e}", "error")
        task.done(False)
    finally:
        task.emit("Cleaning up build directory...", "info")
        task.run_shell(["rm", "-rf", str(work_dir)], sudo=True)


def _configure_arch_chroot(task: Task, profile: BuildProfile, rootfs: Path):
    """Configure an Arch rootfs via arch-chroot."""

    def chroot_run(cmd: list[str]) -> int:
        return task.run_shell(["arch-chroot", str(rootfs)] + cmd, sudo=True)

    chroot_run(["ln", "-sf", f"/usr/share/zoneinfo/{profile.timezone}", "/etc/localtime"])
    chroot_run(["hwclock", "--systohc"])

    chroot_run(["bash", "-c", f"echo '{profile.locale} UTF-8' >> /etc/locale.gen"])
    chroot_run(["locale-gen"])
    chroot_run(["bash", "-c", f"echo 'LANG={profile.locale}' > /etc/locale.conf"])
    chroot_run(["bash", "-c", f"echo 'KEYMAP={profile.keyboard_layout}' > /etc/vconsole.conf"])
    chroot_run(["bash", "-c", f"echo '{profile.hostname}' > /etc/hostname"])

    chroot_run(["useradd", "-m", "-G", "wheel", "-s", "/bin/bash", profile.username])
    if profile.password:
        chroot_run(["bash", "-c", f"echo '{profile.username}:{profile.password}' | chpasswd"])

    # Desktop packages
    de_pkgs = []
    if profile.desktop == "gnome":
        de_pkgs = ["gnome", "gnome-extra", "gdm"]
    elif profile.desktop == "kde":
        de_pkgs = ["plasma-meta", "sddm"]
    elif profile.desktop == "xfce":
        de_pkgs = ["xfce4", "xfce4-goodies", "lightdm", "lightdm-gtk-greeter"]

    all_pkgs = de_pkgs + profile.extra_packages
    if all_pkgs:
        task.emit(f"Installing packages: {', '.join(all_pkgs[:10])}")
        chroot_run(["pacman", "-S", "--noconfirm"] + all_pkgs)

    for svc in profile.enable_services:
        chroot_run(["systemctl", "enable", svc])

    if profile.post_install_script:
        task.emit("Running post-install script...")
        chroot_run(["bash", "-c", profile.post_install_script])

    # Agent OS overlay
    if profile.agent_template:
        _apply_agent_overlay(task, profile, rootfs)

    task.emit("Arch configuration complete.", "success")


def _build_alpine(task: Task, profile: BuildProfile):
    """Build an Alpine Linux rootfs."""

    work_dir = Path(tempfile.mkdtemp(prefix="osmosis-build-", dir=str(BUILD_DIR)))
    rootfs = work_dir / "rootfs"
    rootfs.mkdir()

    try:
        base_info = SUPPORTED_BASES["alpine"]
        version = profile.suite or base_info["default_suite"]
        mirror = f"{base_info['mirror']}/v{version}/main"
        arch = profile.arch if profile.arch in base_info["arch"] else "x86_64"

        task.emit(f"Building Alpine Linux {version} ({arch})...", "info")

        # Generate answer file
        answers = generate_alpine_answers(profile)
        answers_path = work_dir / "answers"
        answers_path.write_text(answers)
        task.emit(f"Answer file saved to {answers_path}", "info")

        base_cache = layer_cache_key("base", distro="alpine", suite=version, arch=arch)
        base_restored = False

        if _ipfs_available():
            cached_cid = layer_cache_lookup(base_cache)
            if cached_cid:
                task.emit(f"Restoring base layer from IPFS cache: {cached_cid[:24]}...", "info")
                base_restored = layer_cache_restore(cached_cid, str(rootfs), task=task)
                if base_restored:
                    task.emit("Base layer restored from cache.", "success")

        if not base_restored:
            # Use apk to bootstrap
            if not _check_tool("apk"):
                task.emit("Alpine apk tools not found. Falling back to debootstrap-style bootstrap...", "warn")
                task.emit("Install alpine-conf or run from an Alpine host for native support.", "warn")
                minirootfs_url = f"https://dl-cdn.alpinelinux.org/alpine/v{version}/releases/{arch}/alpine-minirootfs-{version}.0-{arch}.tar.gz"
                task.emit(f"Downloading Alpine minirootfs from {minirootfs_url}...")
                rc = task.run_shell(["wget", "-q", "-O", str(work_dir / "rootfs.tar.gz"), minirootfs_url])
                if rc != 0:
                    task.emit("Failed to download Alpine minirootfs.", "error")
                    task.done(False)
                    return
                task.run_shell(["tar", "xzf", str(work_dir / "rootfs.tar.gz"), "-C", str(rootfs)], sudo=True)
            else:
                task.emit("Bootstrapping Alpine with apk...")
                rc = task.run_shell(
                    [
                        "apk",
                        "--root",
                        str(rootfs),
                        "--initdb",
                        "--repository",
                        mirror,
                        "--arch",
                        arch,
                        "add",
                        "alpine-base",
                    ],
                    sudo=True,
                )
                if rc != 0:
                    task.emit("Alpine bootstrap failed.", "error")
                    task.done(False)
                    return

            # Cache the base layer
            if _ipfs_available():
                task.emit("Caching base layer to IPFS...", "info")
                base_tar = work_dir / "base-layer.tar.gz"
                rc_tar = task.run_shell(["tar", "czf", str(base_tar), "-C", str(rootfs), "."], sudo=True)
                if rc_tar == 0:
                    cid = layer_cache_save(
                        str(base_tar), base_cache, {"distro": "alpine", "suite": version, "arch": arch}
                    )
                    if cid:
                        task.emit(f"Base layer cached: {cid[:24]}...", "success")
                    base_tar.unlink(missing_ok=True)

        # Basic configuration
        task.run_shell(["bash", "-c", f"echo '{profile.hostname}' > {rootfs}/etc/hostname"], sudo=True)
        task.run_shell(["bash", "-c", f"echo 'nameserver {profile.dns[0]}' > {rootfs}/etc/resolv.conf"], sudo=True)

        # Agent OS overlay
        if profile.agent_template:
            # Mount virtual filesystems for chroot
            for fs, tgt in [("proc", "proc"), ("sysfs", "sys"), ("devtmpfs", "dev")]:
                task.run_shell(["mount", "-t", fs, fs, str(rootfs / tgt)], sudo=True)
            try:
                _apply_agent_overlay(task, profile, rootfs)
            finally:
                for mnt in ["dev", "proc", "sys"]:
                    task.run_shell(["umount", "-lf", str(rootfs / mnt)], sudo=True)

        task.emit("Alpine configuration complete.", "success")
        _collect_layer_cids(profile)
        _package_output(task, profile, rootfs, work_dir)

    except Exception as e:
        task.emit(f"Build failed: {e}", "error")
        task.done(False)
    finally:
        task.emit("Cleaning up build directory...", "info")
        task.run_shell(["rm", "-rf", str(work_dir)], sudo=True)


def _build_fedora(task: Task, profile: BuildProfile):
    """Build a Fedora image using dnf --installroot."""

    if not _check_tool("dnf"):
        task.emit("dnf is not installed. Install it or run from a Fedora/RHEL host.", "error")
        task.done(False)
        return

    work_dir = Path(tempfile.mkdtemp(prefix="osmosis-build-", dir=str(BUILD_DIR)))
    rootfs = work_dir / "rootfs"
    rootfs.mkdir()

    try:
        base_info = SUPPORTED_BASES["fedora"]
        release = profile.suite or base_info["default_suite"]
        arch = profile.arch if profile.arch in base_info["arch"] else "x86_64"

        task.emit(f"Building Fedora {release} ({arch})...", "info")

        # Generate kickstart for reference
        kickstart = generate_kickstart(profile)
        ks_path = work_dir / "kickstart.cfg"
        ks_path.write_text(kickstart)
        task.emit(f"Kickstart saved to {ks_path}", "info")

        base_cache = layer_cache_key("base", distro="fedora", suite=release, arch=arch)
        base_restored = False

        if _ipfs_available():
            cached_cid = layer_cache_lookup(base_cache)
            if cached_cid:
                task.emit(f"Restoring base layer from IPFS cache: {cached_cid[:24]}...", "info")
                base_restored = layer_cache_restore(cached_cid, str(rootfs), task=task)
                if base_restored:
                    task.emit("Base layer restored from cache.", "success")

        if not base_restored:
            # Bootstrap using dnf --installroot
            task.emit("Bootstrapping Fedora with dnf --installroot...", "info")
            repo_url = f"{base_info['mirror']}/releases/{release}/Everything/{arch}/os/"
            rc = task.run_shell(
                [
                    "dnf",
                    "install",
                    "--installroot",
                    str(rootfs),
                    "--releasever",
                    release,
                    "--repo=fedora",
                    "--setopt=reposdir=/dev/null",
                    f"--repofrompath=fedora,{repo_url}",
                    "-y",
                    "--nogpgcheck",
                    "basesystem",
                    "systemd",
                    "dnf",
                    "passwd",
                    "vim-minimal",
                ],
                sudo=True,
            )
            if rc != 0:
                task.emit("Fedora bootstrap failed.", "error")
                task.done(False)
                return

            if _ipfs_available():
                task.emit("Caching base layer to IPFS...", "info")
                base_tar = work_dir / "base-layer.tar.gz"
                rc_tar = task.run_shell(["tar", "czf", str(base_tar), "-C", str(rootfs), "."], sudo=True)
                if rc_tar == 0:
                    cid = layer_cache_save(
                        str(base_tar), base_cache, {"distro": "fedora", "suite": release, "arch": arch}
                    )
                    if cid:
                        task.emit(f"Base layer cached: {cid[:24]}...", "success")
                    base_tar.unlink(missing_ok=True)

        task.emit("Base system installed. Configuring...", "info")

        # Basic configuration
        task.run_shell(["bash", "-c", f"echo '{profile.hostname}' > {rootfs}/etc/hostname"], sudo=True)
        task.run_shell(["bash", "-c", f"echo 'LANG={profile.locale}' > {rootfs}/etc/locale.conf"], sudo=True)

        # Create user
        task.emit(f"Creating user: {profile.username}")
        task.run_shell(
            ["chroot", str(rootfs), "useradd", "-m", "-G", "wheel", "-s", "/bin/bash", profile.username], sudo=True
        )
        if profile.password:
            task.run_shell(
                ["chroot", str(rootfs), "bash", "-c", f"echo '{profile.username}:{profile.password}' | chpasswd"],
                sudo=True,
            )

        # Extra packages
        all_pkgs = list(profile.extra_packages)
        if profile.desktop == "gnome":
            all_pkgs.append("@gnome-desktop")
        elif profile.desktop == "kde":
            all_pkgs.append("@kde-desktop")
        elif profile.desktop == "xfce":
            all_pkgs.append("@xfce-desktop")

        if profile.firewall == "ufw":
            all_pkgs.append("ufw")
        elif profile.firewall == "nftables":
            all_pkgs.append("nftables")
        if profile.ssh_keys:
            all_pkgs.append("openssh-server")

        if all_pkgs:
            task.emit(f"Installing packages: {', '.join(all_pkgs[:10])}{'...' if len(all_pkgs) > 10 else ''}")
            task.run_shell(
                [
                    "dnf",
                    "install",
                    "--installroot",
                    str(rootfs),
                    "--releasever",
                    release,
                    "-y",
                    "--nogpgcheck",
                ]
                + all_pkgs,
                sudo=True,
            )

        # SSH keys
        if profile.ssh_keys:
            ssh_dir = rootfs / "home" / profile.username / ".ssh"
            task.run_shell(["mkdir", "-p", str(ssh_dir)], sudo=True)
            authorized = "\n".join(profile.ssh_keys) + "\n"
            task.run_shell(["bash", "-c", f"echo '{authorized}' > {ssh_dir}/authorized_keys"], sudo=True)
            task.run_shell(["chmod", "700", str(ssh_dir)], sudo=True)
            task.run_shell(["chmod", "600", str(ssh_dir / "authorized_keys")], sudo=True)

        # Post-install
        if profile.post_install_script:
            task.emit("Running post-install script...")
            script_path = rootfs / "tmp" / "osmosis-post-install.sh"
            task.run_shell(
                ["bash", "-c", f"cat > {script_path} << 'SCRIPTEOF'\n{profile.post_install_script}\nSCRIPTEOF"],
                sudo=True,
            )
            task.run_shell(["chroot", str(rootfs), "bash", "/tmp/osmosis-post-install.sh"], sudo=True)

        # Agent OS overlay
        if profile.agent_template:
            _apply_agent_overlay(task, profile, rootfs)

        task.emit("Fedora configuration complete.", "success")
        _collect_layer_cids(profile)
        _package_output(task, profile, rootfs, work_dir)

    except Exception as e:
        task.emit(f"Build failed: {e}", "error")
        task.done(False)
    finally:
        task.emit("Cleaning up build directory...", "info")
        task.run_shell(["rm", "-rf", str(work_dir)], sudo=True)


def _build_nixos(task: Task, profile: BuildProfile):
    """Build a NixOS image using nix-build."""

    if not _check_tool("nix-build"):
        task.emit("nix-build is not installed. Install Nix: https://nixos.org/download.html", "error")
        task.done(False)
        return

    work_dir = Path(tempfile.mkdtemp(prefix="osmosis-build-", dir=str(BUILD_DIR)))

    try:
        release = profile.suite or SUPPORTED_BASES["nixos"]["default_suite"]
        arch = profile.arch if profile.arch in SUPPORTED_BASES["nixos"]["arch"] else "x86_64"

        task.emit(f"Building NixOS {release} ({arch})...", "info")

        # Generate configuration.nix
        nix_config = generate_nix_config(profile)
        config_dir = work_dir / "nixos"
        config_dir.mkdir()
        config_path = config_dir / "configuration.nix"
        config_path.write_text(nix_config)
        task.emit(f"configuration.nix saved to {config_path}", "info")

        # Generate minimal hardware-configuration.nix
        hw_config = (
            "\n".join(
                [
                    "# Osmosis auto-generated hardware configuration (placeholder)",
                    "{ config, lib, pkgs, modulesPath, ... }:",
                    "",
                    "{",
                    "  imports = [ ];",
                    '  boot.initrd.availableKernelModules = [ "ahci" "xhci_pci" "virtio_pci" "sr_mod" "virtio_blk" ];',
                    "  boot.kernelModules = [ ];",
                    '  fileSystems."/" = { device = "/dev/disk/by-label/nixos"; fsType = "ext4"; };',
                    '  fileSystems."/boot" = { device = "/dev/disk/by-label/boot"; fsType = "vfat"; };',
                    "}",
                ]
            )
            + "\n"
        )
        (config_dir / "hardware-configuration.nix").write_text(hw_config)

        # Build the NixOS system image using nix-build
        nixpkgs_channel = f"nixos-{release}"
        task.emit(f"Running nix-build with nixpkgs channel {nixpkgs_channel}...", "info")
        task.emit("This may take a long time on first build (downloading closures).", "info")

        output_name = f"{profile.name}-{profile.base}-{profile.suite}-{profile.arch}"

        if profile.output_format == "iso":
            # Build an ISO via nixos-generators style
            nix_expr = (
                f"let nixpkgs = <nixpkgs>; "
                f'in (import (nixpkgs + "/nixos") {{ '
                f"configuration = {config_path}; "
                f"}}).config.system.build.isoImage"
            )
            rc = task.run_shell(
                [
                    "nix-build",
                    "--no-out-link",
                    "-E",
                    nix_expr,
                    "-I",
                    f"nixpkgs=channel:{nixpkgs_channel}",
                    "-o",
                    str(work_dir / "result"),
                ]
            )
        else:
            # Build a raw disk image
            nix_expr = (
                f"let nixpkgs = <nixpkgs>; "
                f'in (import (nixpkgs + "/nixos") {{ '
                f"configuration = {config_path}; "
                f"}}).config.system.build.toplevel"
            )
            rc = task.run_shell(
                [
                    "nix-build",
                    "--no-out-link",
                    "-E",
                    nix_expr,
                    "-I",
                    f"nixpkgs=channel:{nixpkgs_channel}",
                    "-o",
                    str(work_dir / "result"),
                ]
            )

        if rc != 0:
            task.emit("nix-build failed.", "error")
            task.done(False)
            return

        # Copy the result to the output directory
        result_link = work_dir / "result"
        if result_link.exists():
            ext_map = {"img": ".img", "rootfs": ".tar.gz", "iso": ".iso"}
            ext = ext_map.get(profile.output_format, ".img")
            out_path = OUTPUT_DIR / f"{output_name}{ext}"

            if profile.output_format == "iso":
                # Find the ISO in the result
                task.run_shell(["bash", "-c", f"find {result_link}/iso -name '*.iso' -exec cp {{}} {out_path} \\;"])
            else:
                # Create a rootfs tarball from the closure
                task.emit("Creating rootfs tarball from NixOS closure...", "info")
                task.run_shell(["tar", "czf", str(out_path), "-C", str(result_link), "."], sudo=True)

            task.run_shell(["chown", f"{os.getuid()}:{os.getgid()}", str(out_path)], sudo=True)

        # Save profile
        profile_path = OUTPUT_DIR / f"{output_name}-profile.json"
        profile.save(profile_path)
        task.emit(f"Build profile saved: {profile_path}", "info")
        task.emit("")
        task.emit("NixOS build complete!", "success")
        task.done(True)

    except Exception as e:
        task.emit(f"Build failed: {e}", "error")
        task.done(False)
    finally:
        task.emit("Cleaning up build directory...", "info")
        task.run_shell(["rm", "-rf", str(work_dir)], sudo=True)


def _build_pmos(task: Task, profile: BuildProfile):
    """Build a postmarketOS image using pmbootstrap.

    pmbootstrap handles kernel, device tree, initramfs, and rootfs assembly
    for mobile devices. We configure it, apply any OSmosis patches (e.g.
    codina display/audio DT fixes), build, and export the flashable image.
    """

    if not _check_tool("pmbootstrap"):
        task.emit("pmbootstrap is not installed.", "error")
        task.emit("Install with: pip install pmbootstrap", "error")
        task.emit("See: https://wiki.postmarketos.org/wiki/Pmbootstrap", "info")
        task.done(False)
        return

    # Resolve target device
    target = None
    for dev in TARGET_DEVICES:
        if dev["id"] == profile.target_device and dev.get("pmos_device"):
            target = dev
            break

    if not target:
        task.emit(f"Target device '{profile.target_device}' has no pmOS device mapping.", "error")
        task.emit("pmOS builds require a device with pmos_device set in TARGET_DEVICES.", "info")
        task.done(False)
        return

    pmos_device = target["pmos_device"]
    pmos_channel = profile.suite or "v24.12"
    work_dir = Path(tempfile.mkdtemp(prefix="osmosis-pmos-", dir=str(BUILD_DIR)))

    try:
        task.emit(f"Building postmarketOS for {target['label']}", "info")
        task.emit(f"pmOS device: {pmos_device}", "info")
        task.emit(f"Channel: {pmos_channel}", "info")
        task.emit("")

        # Step 1: Initialize pmbootstrap
        task.emit("Initializing pmbootstrap...", "info")
        pmos_work = work_dir / "pmos"
        pmos_work.mkdir()

        rc = task.run_shell(
            [
                "pmbootstrap",
                "--work",
                str(pmos_work),
                "init",
                "--channel",
                pmos_channel,
                "--device",
                pmos_device,
                "--ui",
                "none",
                "--no-blockdev",
            ]
        )
        if rc != 0:
            task.emit("pmbootstrap init failed.", "error")
            task.done(False)
            return

        # Step 2: Apply OSmosis kernel patches if available
        patches_dir = target.get("patches")
        if patches_dir:
            patches_path = Path(__file__).parent.parent / patches_dir
            if patches_path.exists():
                patch_files = sorted(patches_path.glob("*.patch"))
                if patch_files:
                    task.emit(f"Applying {len(patch_files)} OSmosis kernel patches...", "info")

                    # Find the kernel aport directory
                    kernel_pkg = target.get("kernel", "linux-postmarketos-stericsson")
                    pmaports_dir = pmos_work / "cache_git" / "pmaports"

                    # Search for the kernel package in pmaports
                    kernel_aport = None
                    for search_dir in ["main", "community", "testing"]:
                        candidate = pmaports_dir / search_dir / kernel_pkg
                        if candidate.exists():
                            kernel_aport = candidate
                            break

                    if kernel_aport:
                        for pf in patch_files:
                            task.emit(f"  Copying {pf.name}")
                            task.run_shell(["cp", str(pf), str(kernel_aport / pf.name)])

                        # Add patches to APKBUILD source list
                        apkbuild = kernel_aport / "APKBUILD"
                        if apkbuild.exists():
                            task.emit("  Updating APKBUILD with patch references...")
                            patch_names = " ".join(pf.name for pf in patch_files)
                            # Append patches to source= and add sha512sums
                            task.run_shell(
                                [
                                    "bash",
                                    "-c",
                                    f"cd {kernel_aport} && "
                                    f"sed -i '/^source=/a\\    {patch_names}' APKBUILD && "
                                    f'for p in {patch_names}; do echo "$(sha512sum $p | cut -d" " -f1)  $p" >> checksums.tmp; done',
                                ]
                            )
                            task.emit("  Patches registered in kernel build.", "success")
                    else:
                        task.emit(f"  Warning: kernel aport '{kernel_pkg}' not found in pmaports", "warn")

        # Step 3: Install extra packages (agent overlay packages)
        agent_pkgs = []
        if profile.agent_template:
            agent_pkgs = _agent_overlay_packages(profile.agent_template, "pmos")
        extra_pkgs = list(profile.extra_packages) + agent_pkgs
        # Deduplicate
        seen = set()
        unique_pkgs = []
        for p in extra_pkgs:
            if p not in seen:
                unique_pkgs.append(p)
                seen.add(p)

        if unique_pkgs:
            task.emit(f"Adding packages: {', '.join(unique_pkgs[:10])}{'...' if len(unique_pkgs) > 10 else ''}")
            # Write packages to pmbootstrap config
            rc = task.run_shell(
                [
                    "pmbootstrap",
                    "--work",
                    str(pmos_work),
                    "config",
                    "extra_packages",
                    ",".join(unique_pkgs),
                ]
            )

        # Step 4: Set user and hostname
        task.run_shell(
            [
                "pmbootstrap",
                "--work",
                str(pmos_work),
                "config",
                "hostname",
                profile.hostname,
            ]
        )
        task.run_shell(
            [
                "pmbootstrap",
                "--work",
                str(pmos_work),
                "config",
                "user",
                profile.username,
            ]
        )

        # Step 5: Build the kernel and install the image
        task.emit("")
        task.emit("Building postmarketOS image (this may take a while)...", "info")
        rc = task.run_shell(
            [
                "pmbootstrap",
                "--work",
                str(pmos_work),
                "install",
                "--no-fde",
            ]
        )
        if rc != 0:
            task.emit("pmbootstrap install failed.", "error")
            task.done(False)
            return

        task.emit("pmOS image built successfully.", "success")

        # Step 6: Export the image
        task.emit("")
        task.emit("Exporting flashable image...", "info")
        export_dir = work_dir / "export"
        export_dir.mkdir()
        rc = task.run_shell(
            [
                "pmbootstrap",
                "--work",
                str(pmos_work),
                "export",
                str(export_dir),
            ]
        )
        if rc != 0:
            task.emit("pmbootstrap export failed.", "error")
            task.done(False)
            return

        # Step 7: Apply agent overlay to the rootfs if needed
        if profile.agent_template:
            task.emit("")
            task.emit("Applying agent overlay to pmOS rootfs...", "info")
            # Find the rootfs image and mount it
            rootfs_img = None
            for f in export_dir.iterdir():
                if f.name.endswith(".img") and "rootfs" in f.name.lower():
                    rootfs_img = f
                    break

            if rootfs_img:
                # Mount the rootfs image, apply overlay, unmount
                mount_dir = work_dir / "rootfs_mount"
                mount_dir.mkdir()

                r = subprocess.run(
                    ["sudo", "losetup", "--show", "-fP", str(rootfs_img)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if r.returncode == 0:
                    loop_dev = r.stdout.strip()
                    try:
                        # Try mounting the last partition (rootfs is usually p2 or the only partition)
                        parts = sorted(Path("/dev").glob(f"{Path(loop_dev).name}p*"))
                        root_part = str(parts[-1]) if parts else loop_dev
                        task.run_shell(["mount", root_part, str(mount_dir)], sudo=True)

                        # Mount virtual filesystems for chroot
                        for fs, tgt in [("proc", "proc"), ("sysfs", "sys"), ("devtmpfs", "dev")]:
                            task.run_shell(["mount", "-t", fs, fs, str(mount_dir / tgt)], sudo=True)

                        try:
                            _apply_agent_overlay(task, profile, mount_dir)
                        finally:
                            for mnt in ["dev", "proc", "sys"]:
                                task.run_shell(["umount", "-lf", str(mount_dir / mnt)], sudo=True)
                            task.run_shell(["umount", str(mount_dir)], sudo=True)
                    finally:
                        task.run_shell(["losetup", "-d", loop_dev], sudo=True)
            else:
                task.emit("Warning: could not find rootfs image for agent overlay", "warn")

        # Step 8: Copy exported files to output directory
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_name = f"{profile.name}-pmos-{pmos_channel}-{pmos_device}"
        exported_files = []
        for f in export_dir.iterdir():
            dest = OUTPUT_DIR / f"{output_name}-{f.name}"
            task.run_shell(["cp", str(f), str(dest)])
            task.run_shell(["chown", f"{os.getuid()}:{os.getgid()}", str(dest)], sudo=True)
            size_mb = dest.stat().st_size / (1024 * 1024)
            exported_files.append((dest, size_mb))
            task.emit(f"  {dest.name} ({size_mb:.1f} MB)")

        # Save build profile
        profile_path = OUTPUT_DIR / f"{output_name}-profile.json"
        profile.save(profile_path)

        task.emit("")
        task.emit("pmOS build complete!", "success")
        task.emit("")
        task.emit("Flash with:", "info")
        task.emit(f"  pmbootstrap --work {pmos_work} flasher flash_rootfs --partition USERDATA", "info")
        task.emit(f"  pmbootstrap --work {pmos_work} flasher flash_kernel", "info")
        task.emit("Or use OSmosis flash wizard to flash via Heimdall.", "info")
        task.done(True)

    except Exception as e:
        task.emit(f"Build failed: {e}", "error")
        task.done(False)
    finally:
        # Don't clean up pmos work dir — needed for flashing
        task.emit(f"pmbootstrap work dir preserved at: {pmos_work}", "info")


# ---------------------------------------------------------------------------
# Output packaging
# ---------------------------------------------------------------------------


def _package_output(task: Task, profile: BuildProfile, rootfs: Path, work_dir: Path):
    """Package the rootfs into the requested output format."""

    output_name = f"{profile.name}-{profile.base}-{profile.suite}-{profile.arch}"
    task.emit("")

    if profile.output_format == "rootfs":
        out_path = OUTPUT_DIR / f"{output_name}.tar.gz"
        task.emit(f"Creating rootfs tarball: {out_path}", "info")
        rc = task.run_shell(
            [
                "tar",
                "czf",
                str(out_path),
                "-C",
                str(rootfs),
                ".",
            ],
            sudo=True,
        )
        if rc != 0:
            task.emit("Failed to create tarball.", "error")
            task.done(False)
            return
        # Fix ownership so the user can access it
        task.run_shell(["chown", f"{os.getuid()}:{os.getgid()}", str(out_path)], sudo=True)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        task.emit(f"Rootfs tarball: {out_path} ({size_mb:.1f} MB)", "success")

    elif profile.output_format == "img":
        out_path = OUTPUT_DIR / f"{output_name}.img"
        size_mb = profile.image_size_mb
        task.emit(f"Creating raw disk image: {out_path} ({size_mb} MB)", "info")

        # Create sparse image
        rc = task.run_shell(["truncate", "-s", f"{size_mb}M", str(out_path)])
        if rc != 0:
            task.emit("Failed to create disk image.", "error")
            task.done(False)
            return

        # Partition: 512MB EFI + rest ext4
        task.emit("Partitioning disk image...")
        task.run_shell(["bash", "-c", f"echo -e 'label: gpt\\n,512M,U\\n,,L' | sfdisk {out_path}"], sudo=True)

        # Set up loop device
        task.emit("Attaching loop device...")
        r = subprocess.run(
            ["sudo", "losetup", "--show", "-fP", str(out_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            task.emit("Failed to attach loop device.", "error")
            task.done(False)
            return
        loop_dev = r.stdout.strip()
        task.emit(f"Loop device: {loop_dev}")

        try:
            # Format partitions
            task.emit("Formatting EFI partition (FAT32)...")
            task.run_shell(["mkfs.vfat", "-F32", f"{loop_dev}p1"], sudo=True)
            task.emit("Formatting root partition (ext4)...")
            task.run_shell(["mkfs.ext4", "-q", "-L", "osmosis-root", f"{loop_dev}p2"], sudo=True)

            # Mount and copy rootfs
            img_mount = work_dir / "img_mount"
            img_mount.mkdir()
            task.run_shell(["mount", f"{loop_dev}p2", str(img_mount)], sudo=True)
            efi_mount = img_mount / "boot" / "efi"
            task.run_shell(["mkdir", "-p", str(efi_mount)], sudo=True)
            task.run_shell(["mount", f"{loop_dev}p1", str(efi_mount)], sudo=True)

            task.emit("Copying rootfs to disk image...")
            task.run_shell(["cp", "-a", f"{rootfs}/.", str(img_mount)], sudo=True)

            # Install bootloader
            task.emit("Installing GRUB bootloader...")
            task.run_shell(
                [
                    "grub-install",
                    "--target=x86_64-efi",
                    f"--efi-directory={efi_mount}",
                    "--boot-directory=" + str(img_mount / "boot"),
                    "--removable",
                    "--no-nvram",
                ],
                sudo=True,
            )

            task.run_shell(["umount", str(efi_mount)], sudo=True)
            task.run_shell(["umount", str(img_mount)], sudo=True)

        finally:
            task.run_shell(["losetup", "-d", loop_dev], sudo=True)

        # Fix ownership
        task.run_shell(["chown", f"{os.getuid()}:{os.getgid()}", str(out_path)], sudo=True)
        size_actual = out_path.stat().st_size / (1024 * 1024)
        task.emit(f"Disk image: {out_path} ({size_actual:.1f} MB)", "success")

    elif profile.output_format == "iso":
        out_path = OUTPUT_DIR / f"{output_name}.iso"
        task.emit(f"Creating bootable ISO: {out_path}", "info")

        if not _check_tool("xorriso"):
            task.emit("xorriso not installed. Install it with: sudo apt install xorriso", "error")
            task.done(False)
            return

        # Create ISO staging area
        iso_stage = work_dir / "iso_stage"
        iso_stage.mkdir()
        task.run_shell(["cp", "-a", f"{rootfs}/.", str(iso_stage)], sudo=True)

        rc = task.run_shell(
            [
                "xorriso",
                "-as",
                "mkisofs",
                "-o",
                str(out_path),
                "-isohybrid-mbr",
                "/usr/lib/ISOLINUX/isohdpfx.bin",
                "-c",
                "isolinux/boot.cat",
                "-b",
                "isolinux/isolinux.bin",
                "-no-emul-boot",
                "-boot-load-size",
                "4",
                "-boot-info-table",
                str(iso_stage),
            ],
            sudo=True,
        )
        if rc != 0:
            task.emit("ISO creation failed.", "error")
            task.done(False)
            return

        task.run_shell(["chown", f"{os.getuid()}:{os.getgid()}", str(out_path)], sudo=True)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        task.emit(f"ISO image: {out_path} ({size_mb:.1f} MB)", "success")

    else:
        task.emit(f"Unknown output format: {profile.output_format}", "error")
        task.done(False)
        return

    # Save profile alongside the output
    profile_path = OUTPUT_DIR / f"{output_name}-profile.json"
    profile.save(profile_path)
    task.emit(f"Build profile saved: {profile_path}", "info")
    task.emit("")
    task.emit("OS build complete!", "success")
    task.done(True)


# ---------------------------------------------------------------------------
# Profile management helpers
# ---------------------------------------------------------------------------


def list_profiles() -> list[dict]:
    """List saved build profiles."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profiles = []
    for f in sorted(PROFILES_DIR.glob("*.json")):
        try:
            p = BuildProfile.load(f)
            profiles.append({**p.to_dict(), "_path": str(f)})
        except Exception:  # noqa: S112
            continue
    return profiles


def estimate_image_size(profile: BuildProfile) -> dict:
    """Rough size estimate for the build output."""
    base_sizes = {
        "ubuntu": 300,
        "debian": 200,
        "arch": 500,
        "alpine": 50,
        "fedora": 400,
        "nixos": 600,
    }
    base = base_sizes.get(profile.base, 300)

    desktop_sizes = {
        "none": 0,
        "gnome": 1200,
        "kde": 1000,
        "xfce": 400,
        "lxqt": 300,
        "i3": 150,
        "sway": 200,
    }
    de = desktop_sizes.get(profile.desktop, 0)

    pkg_estimate = len(profile.extra_packages) * 10

    # Agent OS overlay adds system packages, pip packages, and the agent repo
    agent_mb = 0
    if profile.agent_template:
        tmpl = AGENT_OS_TEMPLATES.get(profile.agent_template, {})
        agent_mb += len(tmpl.get("system_packages", [])) * 15
        agent_mb += len(tmpl.get("pip_packages", [])) * 50  # pip packages tend to be larger
        agent_mb += len(tmpl.get("kiosk_packages", [])) * 10
        agent_mb += 50  # repo clone + venv overhead

    total = base + de + pkg_estimate + agent_mb

    return {
        "base_mb": base,
        "desktop_mb": de,
        "packages_mb": pkg_estimate,
        "agent_overlay_mb": agent_mb,
        "total_mb": total,
        "recommended_image_mb": max(total * 2, 2048),
    }
