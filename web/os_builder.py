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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUILD_DIR = Path.home() / ".osmosis" / "os-builder"
PROFILES_DIR = BUILD_DIR / "profiles"
OUTPUT_DIR = Path.home() / "Osmosis-downloads" / "os-builds"

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
]


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
        lines.extend([
            f"d-i netcfg/get_ipaddress string {profile.static_ip}",
            f"d-i netcfg/get_gateway string {profile.gateway}",
            f"d-i netcfg/get_nameservers string {' '.join(profile.dns)}",
        ])

    # Disk
    if profile.disk_layout == "auto":
        lines.extend([
            "d-i partman-auto/method string regular",
            "d-i partman-auto/choose_recipe select atomic",
            "d-i partman/confirm boolean true",
            "d-i partman/confirm_nooverwrite boolean true",
        ])
    elif profile.disk_layout == "lvm":
        lines.extend([
            "d-i partman-auto/method string lvm",
            "d-i partman-lvm/confirm boolean true",
            "d-i partman-lvm/device_remove_lvm boolean true",
        ])
    elif profile.disk_layout == "luks":
        lines.extend([
            "d-i partman-auto/method string crypto",
            "d-i partman-crypto/passphrase string placeholder",
            "d-i partman-crypto/passphrase-again string placeholder",
        ])

    # User
    lines.extend([
        f"d-i passwd/username string {profile.username}",
        "d-i passwd/user-password-crypted string !",
        "d-i user-setup/allow-password-weak boolean true",
    ])

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
        f"KEYMAPOPTS=\"{profile.keyboard_layout} {profile.keyboard_layout}\"",
        f"HOSTNAMEOPTS=\"-n {profile.hostname}\"",
        "INTERFACESOPTS=\"auto lo",
        "iface lo inet loopback",
        "",
        "auto eth0",
    ]
    if profile.network == "dhcp":
        lines.append("iface eth0 inet dhcp\"")
    else:
        lines.extend([
            f"iface eth0 inet static",
            f"    address {profile.static_ip}",
            f"    gateway {profile.gateway}\"",
        ])

    lines.extend([
        "DNSOPTS=\"-d example.com " + " ".join(profile.dns) + "\"",
        f"TIMEZONEOPTS=\"-z {profile.timezone}\"",
        "PROXYOPTS=\"none\"",
        "APKREPOSOPTS=\"-1\"",
        "SSHDOPTS=\"-c openssh\"",
        "NTPOPTS=\"-c chrony\"",
        "DISKOPTS=\"-m sys /dev/sda\"",
    ])
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
        f"HOSTNAME=\"{profile.hostname}\"",
        f"USERNAME=\"{profile.username}\"",
        f"LOCALE=\"{profile.locale}\"",
        f"TIMEZONE=\"{profile.timezone}\"",
        f"KEYMAP=\"{profile.keyboard_layout}\"",
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
        f"echo \"{profile.locale} UTF-8\" >> /etc/locale.gen",
        "locale-gen",
        f"echo \"LANG={profile.locale}\" > /etc/locale.conf",
        f"echo \"KEYMAP={profile.keyboard_layout}\" > /etc/vconsole.conf",
        f"echo \"{profile.hostname}\" > /etc/hostname",
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
        lines.extend([
            "pacman -S --noconfirm ufw",
            "systemctl enable ufw",
            *[f"ufw allow {svc}" for svc in profile.firewall_allow],
            "ufw --force enable",
        ])

    for svc in profile.enable_services:
        lines.append(f"systemctl enable {svc}")
    for svc in profile.disable_services:
        lines.append(f"systemctl disable {svc}")

    lines.extend(["CHROOT", ""])

    if profile.post_install_script:
        lines.extend([
            "# User post-install script",
            f"arch-chroot $MOUNT /bin/bash <<'POSTSCRIPT'",
            profile.post_install_script,
            "POSTSCRIPT",
            "",
        ])

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


def build_os(task: Task, profile: BuildProfile):
    """Main build entry point — runs in a background Task thread."""

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
        # Step 1: debootstrap
        base_info = SUPPORTED_BASES[profile.base]
        suite = profile.suite or base_info["default_suite"]
        mirror = base_info["mirror"]

        task.emit(f"Running debootstrap for {profile.base} {suite} ({profile.arch})...", "info")
        task.emit("This may take several minutes depending on your connection.", "info")
        task.emit("")

        debootstrap_cmd = [
            "debootstrap",
            "--arch", profile.arch,
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
            task.emit(f"Installing packages: {', '.join(all_pkgs[:10])}{'...' if len(all_pkgs) > 10 else ''}")
            chroot_run(["bash", "-c", "apt-get update -qq"])
            chroot_run(["bash", "-c",
                         "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends " +
                         " ".join(all_pkgs)])

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
                f"Gateway={profile.gateway}\n"
                + "".join(f"DNS={d}\n" for d in profile.dns)
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

        task.emit("Running pacstrap...", "info")
        # Run pacstrap directly (the script expects $MOUNT to be ready)
        pkgs = ["base", "linux", "linux-firmware"]
        rc = task.run_shell(["pacstrap", str(rootfs)] + pkgs, sudo=True)
        if rc != 0:
            task.emit("pacstrap failed.", "error")
            task.done(False)
            return

        # Generate fstab
        task.run_shell(["bash", "-c", f"genfstab -U {rootfs} >> {rootfs}/etc/fstab"], sudo=True)

        # Configure via chroot
        task.emit("Configuring Arch system...", "info")
        _configure_arch_chroot(task, profile, rootfs)

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

        # Use apk to bootstrap
        if not _check_tool("apk"):
            task.emit("Alpine apk tools not found. Falling back to debootstrap-style bootstrap...", "warn")
            task.emit("Install alpine-conf or run from an Alpine host for native support.", "warn")
            # Fallback: download and extract a minirootfs
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
            rc = task.run_shell([
                "apk", "--root", str(rootfs), "--initdb",
                "--repository", mirror,
                "--arch", arch,
                "add", "alpine-base",
            ], sudo=True)
            if rc != 0:
                task.emit("Alpine bootstrap failed.", "error")
                task.done(False)
                return

        # Basic configuration
        task.run_shell(["bash", "-c", f"echo '{profile.hostname}' > {rootfs}/etc/hostname"], sudo=True)
        task.run_shell(["bash", "-c",
                         f"echo 'nameserver {profile.dns[0]}' > {rootfs}/etc/resolv.conf"], sudo=True)

        task.emit("Alpine configuration complete.", "success")
        _package_output(task, profile, rootfs, work_dir)

    except Exception as e:
        task.emit(f"Build failed: {e}", "error")
        task.done(False)
    finally:
        task.emit("Cleaning up build directory...", "info")
        task.run_shell(["rm", "-rf", str(work_dir)], sudo=True)


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
        rc = task.run_shell([
            "tar", "czf", str(out_path), "-C", str(rootfs), ".",
        ], sudo=True)
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
        task.run_shell(["bash", "-c",
                         f"echo -e 'label: gpt\\n,512M,U\\n,,L' | sfdisk {out_path}"], sudo=True)

        # Set up loop device
        task.emit("Attaching loop device...")
        r = subprocess.run(
            ["sudo", "losetup", "--show", "-fP", str(out_path)],
            capture_output=True, text=True, timeout=10,
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
            task.run_shell([
                "grub-install", "--target=x86_64-efi",
                f"--efi-directory={efi_mount}",
                "--boot-directory=" + str(img_mount / "boot"),
                "--removable", "--no-nvram",
            ], sudo=True)

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

        rc = task.run_shell([
            "xorriso", "-as", "mkisofs",
            "-o", str(out_path),
            "-isohybrid-mbr", "/usr/lib/ISOLINUX/isohdpfx.bin",
            "-c", "isolinux/boot.cat",
            "-b", "isolinux/isolinux.bin",
            "-no-emul-boot", "-boot-load-size", "4", "-boot-info-table",
            str(iso_stage),
        ], sudo=True)
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
        except Exception:
            continue
    return profiles


def estimate_image_size(profile: BuildProfile) -> dict:
    """Rough size estimate for the build output."""
    base_sizes = {
        "ubuntu": 300,
        "debian": 200,
        "arch": 500,
        "alpine": 50,
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
    total = base + de + pkg_estimate

    return {
        "base_mb": base,
        "desktop_mb": de,
        "packages_mb": pkg_estimate,
        "total_mb": total,
        "recommended_image_mb": max(total * 2, 2048),
    }
