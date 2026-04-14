"""Mobile security ruleset — compliance rules for phones, tablets, and devices.

Each rule has a check function that queries the device via ADB to verify
the security property at runtime.  Rules are organized by category:

    B## — Boot chain (verified boot, bootloader, secure boot)
    E## — Encryption (FDE/FBE, key storage)
    N## — Network (firewall, DNS, Tor, IPv6)
    M## — Modem/baseband isolation
    A## — App sandboxing and permissions
    U## — Update mechanism (OTA, signatures)
    P## — Privacy (trackers, telemetry, sensors)
    H## — Hardware security (TEE, secure element)

Import this module to auto-register all rules with the compliance engine.
"""

from web.compliance import (
    ComplianceRule,
    RuleResult,
    _getprop,
    _shell,
    register_rule,
)

# ===================================================================
# B — Boot chain
# ===================================================================

register_rule(
    ComplianceRule(
        id="B01",
        name="Verified Boot enabled",
        description=(
            "Android Verified Boot (AVB) ensures the integrity of the boot "
            "chain from bootloader through kernel and system partitions."
        ),
        severity="minimal",
        category="boot",
        tags=["boot", "avb"],
        reference="https://source.android.com/docs/security/features/verifiedboot",
    ),
    lambda serial, arch: _check_verified_boot(serial),
)


def _check_verified_boot(serial):
    state = _getprop(serial, "ro.boot.verifiedbootstate")
    if state is None:
        return RuleResult(
            rule_id="B01", rule_name="Verified Boot enabled",
            enabled=True, passed=None,
            detail="Could not read ro.boot.verifiedbootstate",
            severity="minimal", category="boot",
        )
    ok = state in ("green", "yellow")
    return RuleResult(
        rule_id="B01", rule_name="Verified Boot enabled",
        enabled=True, passed=ok,
        detail=f"Verified boot state: {state}" + (
            "" if ok else " — boot chain not verified (orange/red)"
        ),
        severity="minimal", category="boot",
    )


register_rule(
    ComplianceRule(
        id="B02",
        name="Bootloader locked or re-locked",
        description=(
            "A locked bootloader prevents unauthorized OS images from being "
            "flashed. For custom ROMs, re-locking with custom keys is ideal."
        ),
        severity="hardened",
        category="boot",
        tags=["boot", "bootloader"],
    ),
    lambda serial, arch: _check_bootloader_lock(serial),
)


def _check_bootloader_lock(serial):
    unlocked = _getprop(serial, "ro.boot.flash.locked")
    if unlocked is None:
        # Try alternate property
        unlocked = _getprop(serial, "ro.boot.verifiedbootstate")
        if unlocked == "orange":
            return RuleResult(
                rule_id="B02", rule_name="Bootloader locked or re-locked",
                enabled=True, passed=False,
                detail="Bootloader unlocked (AVB state: orange)",
                severity="hardened", category="boot",
            )
    if unlocked == "1":
        return RuleResult(
            rule_id="B02", rule_name="Bootloader locked or re-locked",
            enabled=True, passed=True,
            detail="Bootloader is locked",
            severity="hardened", category="boot",
        )
    return RuleResult(
        rule_id="B02", rule_name="Bootloader locked or re-locked",
        enabled=True, passed=None,
        detail="Could not determine bootloader lock state",
        severity="hardened", category="boot",
    )


register_rule(
    ComplianceRule(
        id="B03",
        name="SELinux enforcing",
        description="SELinux must be in enforcing mode, not permissive.",
        severity="minimal",
        category="boot",
        tags=["selinux"],
    ),
    lambda serial, arch: _check_selinux(serial),
)


def _check_selinux(serial):
    status = _shell(serial, "getenforce")
    if status is None:
        return RuleResult(
            rule_id="B03", rule_name="SELinux enforcing",
            enabled=True, passed=None,
            detail="Could not query SELinux status",
            severity="minimal", category="boot",
        )
    enforcing = status.strip().lower() == "enforcing"
    return RuleResult(
        rule_id="B03", rule_name="SELinux enforcing",
        enabled=True, passed=enforcing,
        detail=f"SELinux: {status.strip()}",
        severity="minimal", category="boot",
    )


# ===================================================================
# E — Encryption
# ===================================================================

register_rule(
    ComplianceRule(
        id="E01",
        name="Storage encryption active",
        description=(
            "Full-disk encryption (FDE) or file-based encryption (FBE) must "
            "be active. FBE is preferred on Android 10+."
        ),
        severity="minimal",
        category="encryption",
        tags=["encryption", "fbe", "fde"],
    ),
    lambda serial, arch: _check_encryption(serial),
)


def _check_encryption(serial):
    # Check FBE first (modern devices)
    fbe = _getprop(serial, "ro.crypto.type")
    if fbe == "file":
        return RuleResult(
            rule_id="E01", rule_name="Storage encryption active",
            enabled=True, passed=True,
            detail="File-based encryption (FBE) active",
            severity="minimal", category="encryption",
        )
    # Check FDE
    state = _getprop(serial, "ro.crypto.state")
    if state == "encrypted":
        return RuleResult(
            rule_id="E01", rule_name="Storage encryption active",
            enabled=True, passed=True,
            detail="Full-disk encryption (FDE) active",
            severity="minimal", category="encryption",
        )
    if state == "unencrypted":
        return RuleResult(
            rule_id="E01", rule_name="Storage encryption active",
            enabled=True, passed=False,
            detail="Device storage is NOT encrypted",
            severity="minimal", category="encryption",
        )
    return RuleResult(
        rule_id="E01", rule_name="Storage encryption active",
        enabled=True, passed=None,
        detail=f"Encryption state unclear: type={fbe}, state={state}",
        severity="minimal", category="encryption",
    )


register_rule(
    ComplianceRule(
        id="E02",
        name="Hardware-backed keystore",
        description=(
            "Cryptographic keys should be stored in a hardware-backed "
            "keystore (TEE or StrongBox) rather than software-only."
        ),
        severity="standard",
        category="encryption",
        tags=["encryption", "tee", "keystore"],
    ),
    lambda serial, arch: _check_hw_keystore(serial),
)


def _check_hw_keystore(serial):
    # Check for hardware security level
    features = _shell(serial, "pm list features")
    if features is None:
        return RuleResult(
            rule_id="E02", rule_name="Hardware-backed keystore",
            enabled=True, passed=None,
            detail="Could not query device features",
            severity="standard", category="encryption",
        )
    has_strongbox = "android.hardware.strongbox_keystore" in features
    has_hw_keystore = "android.hardware.hardware_keystore" in features
    if has_strongbox:
        return RuleResult(
            rule_id="E02", rule_name="Hardware-backed keystore",
            enabled=True, passed=True,
            detail="StrongBox hardware keystore available",
            severity="standard", category="encryption",
        )
    if has_hw_keystore:
        return RuleResult(
            rule_id="E02", rule_name="Hardware-backed keystore",
            enabled=True, passed=True,
            detail="TEE-backed hardware keystore available",
            severity="standard", category="encryption",
        )
    return RuleResult(
        rule_id="E02", rule_name="Hardware-backed keystore",
        enabled=True, passed=False,
        detail="No hardware-backed keystore detected",
        severity="standard", category="encryption",
    )


# ===================================================================
# N — Network
# ===================================================================

register_rule(
    ComplianceRule(
        id="N01",
        name="Private DNS enabled",
        description=(
            "DNS-over-TLS or DNS-over-HTTPS should be active to prevent "
            "DNS queries from being intercepted."
        ),
        severity="standard",
        category="network",
        tags=["network", "dns"],
    ),
    lambda serial, arch: _check_private_dns(serial),
)


def _check_private_dns(serial):
    mode = _shell(serial, "settings get global private_dns_mode")
    if mode is None:
        return RuleResult(
            rule_id="N01", rule_name="Private DNS enabled",
            enabled=True, passed=None,
            detail="Could not query DNS settings",
            severity="standard", category="network",
        )
    mode = mode.strip()
    ok = mode in ("hostname", "opportunistic")
    return RuleResult(
        rule_id="N01", rule_name="Private DNS enabled",
        enabled=True, passed=ok,
        detail=f"Private DNS mode: {mode}" + (
            "" if ok else " — DNS queries may be visible to network observers"
        ),
        severity="standard", category="network",
    )


register_rule(
    ComplianceRule(
        id="N02",
        name="No captive portal check to Google",
        description=(
            "The default Android captive portal check pings Google servers, "
            "leaking connectivity status. Should use a privacy-respecting "
            "endpoint or be disabled."
        ),
        severity="standard",
        category="network",
        tags=["network", "privacy", "google"],
    ),
    lambda serial, arch: _check_captive_portal(serial),
)


def _check_captive_portal(serial):
    url = _shell(
        serial,
        "settings get global captive_portal_https_url",
    )
    mode = _shell(
        serial,
        "settings get global captive_portal_mode",
    )
    if mode and mode.strip() == "0":
        return RuleResult(
            rule_id="N02", rule_name="No captive portal check to Google",
            enabled=True, passed=True,
            detail="Captive portal detection disabled",
            severity="standard", category="network",
        )
    if url and "google" not in url.lower() and url.strip() not in ("null", ""):
        return RuleResult(
            rule_id="N02", rule_name="No captive portal check to Google",
            enabled=True, passed=True,
            detail=f"Custom captive portal endpoint: {url.strip()[:60]}",
            severity="standard", category="network",
        )
    return RuleResult(
        rule_id="N02", rule_name="No captive portal check to Google",
        enabled=True, passed=False,
        detail="Captive portal checks still use default Google servers",
        severity="standard", category="network",
    )


register_rule(
    ComplianceRule(
        id="N03",
        name="IPv6 privacy extensions",
        description=(
            "If IPv6 is enabled, privacy extensions (RFC 4941) should be "
            "active to prevent tracking via stable SLAAC addresses."
        ),
        severity="standard",
        category="network",
        tags=["network", "ipv6"],
    ),
    lambda serial, arch: _check_ipv6_privacy(serial),
)


def _check_ipv6_privacy(serial):
    val = _shell(
        serial,
        "cat /proc/sys/net/ipv6/conf/all/use_tempaddr",
    )
    if val is None:
        return RuleResult(
            rule_id="N03", rule_name="IPv6 privacy extensions",
            enabled=True, passed=None,
            detail="Could not read IPv6 privacy extension setting",
            severity="standard", category="network",
        )
    val = val.strip()
    # 2 = prefer temporary addresses, 1 = use them, 0 = disabled
    ok = val in ("1", "2")
    return RuleResult(
        rule_id="N03", rule_name="IPv6 privacy extensions",
        enabled=True, passed=ok,
        detail=f"use_tempaddr={val}" + (
            " (privacy extensions active)" if ok
            else " — stable IPv6 addresses may enable tracking"
        ),
        severity="standard", category="network",
    )


# ===================================================================
# M — Modem / baseband isolation
# ===================================================================

register_rule(
    ComplianceRule(
        id="M01",
        name="Baseband version identified",
        description=(
            "The baseband/modem firmware version should be identifiable for "
            "vulnerability tracking. Unknown baseband = unknown attack surface."
        ),
        severity="minimal",
        category="baseband",
        tags=["baseband", "modem"],
    ),
    lambda serial, arch: _check_baseband(serial),
)


def _check_baseband(serial):
    version = _getprop(serial, "gsm.version.baseband")
    if not version or version in ("", "unknown"):
        return RuleResult(
            rule_id="M01", rule_name="Baseband version identified",
            enabled=True, passed=False,
            detail="Baseband version unknown — cannot track vulnerabilities",
            severity="minimal", category="baseband",
        )
    return RuleResult(
        rule_id="M01", rule_name="Baseband version identified",
        enabled=True, passed=True,
        detail=f"Baseband: {version}",
        severity="minimal", category="baseband",
    )


register_rule(
    ComplianceRule(
        id="M02",
        name="Airplane mode radio state",
        description=(
            "When airplane mode is on, all radios (cell, WiFi, Bluetooth) "
            "should be fully disabled. Some devices leave radios partially "
            "active even in airplane mode."
        ),
        severity="hardened",
        category="baseband",
        tags=["baseband", "radio", "airplane"],
    ),
    lambda serial, arch: _check_airplane_radios(serial),
)


def _check_airplane_radios(serial):
    airplane = _shell(
        serial, "settings get global airplane_mode_on"
    )
    if airplane is None or airplane.strip() != "1":
        return RuleResult(
            rule_id="M02", rule_name="Airplane mode radio state",
            enabled=True, passed=None,
            detail="Airplane mode is off — check not applicable in this state",
            severity="hardened", category="baseband",
        )
    # Check if radios are actually off
    wifi = _shell(serial, "settings get global wifi_on")
    bt = _shell(serial, "settings get global bluetooth_on")
    radios_off = (
        wifi and wifi.strip() == "0"
        and bt and bt.strip() == "0"
    )
    return RuleResult(
        rule_id="M02", rule_name="Airplane mode radio state",
        enabled=True, passed=radios_off,
        detail="All radios disabled in airplane mode" if radios_off
        else f"Radios still active: wifi={wifi}, bt={bt}",
        severity="hardened", category="baseband",
    )


# ===================================================================
# A — App sandboxing and permissions
# ===================================================================

register_rule(
    ComplianceRule(
        id="A01",
        name="No ADB over network",
        description=(
            "ADB should only be accessible via USB, not over the network. "
            "Network ADB exposes a root-equivalent attack surface."
        ),
        severity="minimal",
        category="app",
        tags=["adb", "network"],
    ),
    lambda serial, arch: _check_adb_network(serial),
)


def _check_adb_network(serial):
    port = _getprop(serial, "service.adb.tcp.port")
    if port and port.strip() not in ("-1", "0", ""):
        return RuleResult(
            rule_id="A01", rule_name="No ADB over network",
            enabled=True, passed=False,
            detail=f"ADB listening on TCP port {port.strip()}",
            severity="minimal", category="app",
        )
    return RuleResult(
        rule_id="A01", rule_name="No ADB over network",
        enabled=True, passed=True,
        detail="ADB is USB-only (no TCP listener)",
        severity="minimal", category="app",
    )


register_rule(
    ComplianceRule(
        id="A02",
        name="Unknown sources disabled",
        description=(
            "Installing apps from unknown sources should be disabled at "
            "the system level. Per-app exceptions are acceptable."
        ),
        severity="standard",
        category="app",
        tags=["app", "sideload"],
    ),
    lambda serial, arch: _check_unknown_sources(serial),
)


def _check_unknown_sources(serial):
    val = _shell(
        serial, "settings get secure install_non_market_apps"
    )
    if val is None:
        return RuleResult(
            rule_id="A02", rule_name="Unknown sources disabled",
            enabled=True, passed=None,
            detail="Could not query install_non_market_apps setting",
            severity="standard", category="app",
        )
    disabled = val.strip() == "0"
    return RuleResult(
        rule_id="A02", rule_name="Unknown sources disabled",
        enabled=True, passed=disabled,
        detail="Unknown sources disabled" if disabled
        else "Unknown sources enabled — apps can be sideloaded without review",
        severity="standard", category="app",
    )


register_rule(
    ComplianceRule(
        id="A03",
        name="Developer options disabled",
        description=(
            "Developer options should be disabled on production devices. "
            "Enabled developer options expose debugging interfaces."
        ),
        severity="standard",
        category="app",
        tags=["developer", "debug"],
    ),
    lambda serial, arch: _check_dev_options(serial),
)


def _check_dev_options(serial):
    val = _shell(
        serial, "settings get global development_settings_enabled"
    )
    if val is None or val.strip() in ("null", ""):
        return RuleResult(
            rule_id="A03", rule_name="Developer options disabled",
            enabled=True, passed=True,
            detail="Developer options not enabled",
            severity="standard", category="app",
        )
    disabled = val.strip() == "0"
    return RuleResult(
        rule_id="A03", rule_name="Developer options disabled",
        enabled=True, passed=disabled,
        detail="Developer options disabled" if disabled
        else "Developer options enabled — debugging interfaces exposed",
        severity="standard", category="app",
    )


# ===================================================================
# U — Update mechanism
# ===================================================================

register_rule(
    ComplianceRule(
        id="U01",
        name="Security patch level current",
        description=(
            "The Android security patch level should be within 90 days of "
            "the current date. Older patches leave known CVEs unpatched."
        ),
        severity="minimal",
        category="update",
        tags=["update", "patch"],
    ),
    lambda serial, arch: _check_patch_level(serial),
)


def _check_patch_level(serial):
    patch = _getprop(serial, "ro.build.version.security_patch")
    if not patch:
        return RuleResult(
            rule_id="U01", rule_name="Security patch level current",
            enabled=True, passed=None,
            detail="Could not read security patch level",
            severity="minimal", category="update",
        )
    try:
        from datetime import datetime, timezone
        patch_date = datetime.strptime(patch.strip(), "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        now = datetime.now(timezone.utc)
        age_days = (now - patch_date).days
        ok = age_days <= 90
        return RuleResult(
            rule_id="U01", rule_name="Security patch level current",
            enabled=True, passed=ok,
            detail=f"Patch level: {patch.strip()} ({age_days} days old)" + (
                "" if ok else " — device is behind on security updates"
            ),
            severity="minimal", category="update",
        )
    except ValueError:
        return RuleResult(
            rule_id="U01", rule_name="Security patch level current",
            enabled=True, passed=None,
            detail=f"Could not parse patch date: {patch}",
            severity="minimal", category="update",
        )


# ===================================================================
# P — Privacy
# ===================================================================

register_rule(
    ComplianceRule(
        id="P01",
        name="No Google Play Services",
        description=(
            "Google Play Services is a persistent background service with "
            "broad permissions and telemetry. Privacy-hardened devices "
            "should use microG or no GMS at all."
        ),
        severity="standard",
        category="privacy",
        tags=["privacy", "google", "gms"],
    ),
    lambda serial, arch: _check_no_gms(serial),
)


def _check_no_gms(serial):
    packages = _shell(serial, "pm list packages com.google.android.gms")
    if packages is None:
        return RuleResult(
            rule_id="P01", rule_name="No Google Play Services",
            enabled=True, passed=None,
            detail="Could not query installed packages",
            severity="standard", category="privacy",
        )
    has_gms = "com.google.android.gms" in packages
    return RuleResult(
        rule_id="P01", rule_name="No Google Play Services",
        enabled=True, passed=not has_gms,
        detail="Google Play Services not installed" if not has_gms
        else "Google Play Services is installed — telemetry and tracking active",
        severity="standard", category="privacy",
    )


register_rule(
    ComplianceRule(
        id="P02",
        name="Screen lock enabled",
        description="A screen lock (PIN, password, pattern, or biometric) must be set.",
        severity="minimal",
        category="auth",
        tags=["auth", "screenlock"],
    ),
    lambda serial, arch: _check_screen_lock(serial),
)


def _check_screen_lock(serial):
    val = _shell(serial, "settings get secure lockscreen.password_type")
    if val is None or val.strip() in ("null", ""):
        # Try alternate: check if lock screen is disabled
        disabled = _shell(
            serial, "settings get secure lockscreen.disabled"
        )
        if disabled and disabled.strip() == "1":
            return RuleResult(
                rule_id="P02", rule_name="Screen lock enabled",
                enabled=True, passed=False,
                detail="Screen lock is explicitly disabled",
                severity="minimal", category="auth",
            )
        return RuleResult(
            rule_id="P02", rule_name="Screen lock enabled",
            enabled=True, passed=None,
            detail="Could not determine screen lock state",
            severity="minimal", category="auth",
        )
    # password_type: 0 = none, 65536 = pattern, 131072+ = PIN/password
    try:
        pw_type = int(val.strip())
        ok = pw_type > 0
        labels = {0: "none", 65536: "pattern"}
        label = labels.get(pw_type, "PIN/password/biometric")
        return RuleResult(
            rule_id="P02", rule_name="Screen lock enabled",
            enabled=True, passed=ok,
            detail=f"Screen lock type: {label}" + (
                "" if ok else " — device has no screen lock"
            ),
            severity="minimal", category="auth",
        )
    except ValueError:
        return RuleResult(
            rule_id="P02", rule_name="Screen lock enabled",
            enabled=True, passed=None,
            detail=f"Unexpected password_type value: {val}",
            severity="minimal", category="auth",
        )


# ===================================================================
# H — Hardware security
# ===================================================================

register_rule(
    ComplianceRule(
        id="H01",
        name="USB debugging authorization required",
        description=(
            "USB debugging should require explicit authorization per host "
            "computer. Disabling this allows any USB connection to access ADB."
        ),
        severity="minimal",
        category="auth",
        tags=["adb", "usb", "auth"],
    ),
    lambda serial, arch: _check_adb_auth(serial),
)


def _check_adb_auth(serial):
    val = _getprop(serial, "ro.adb.secure")
    if val is None:
        return RuleResult(
            rule_id="H01", rule_name="USB debugging authorization required",
            enabled=True, passed=None,
            detail="Could not read ro.adb.secure",
            severity="minimal", category="auth",
        )
    secure = val.strip() == "1"
    return RuleResult(
        rule_id="H01", rule_name="USB debugging authorization required",
        enabled=True, passed=secure,
        detail="ADB requires host authorization" if secure
        else "ADB accepts connections without authorization",
        severity="minimal", category="auth",
    )
