"""Compliance-as-code engine — structured security rules with runtime checks.

Inspired by Sécurix (cloud-gouv/securix) ANSSI compliance framework.
Each security property is a first-class object with:
  - enforcement description (what the rule ensures)
  - check function (runtime verification via ADB/fastboot/local inspection)
  - metadata (severity, category, tags, reference)
  - mandatory exclusion rationale (you can't silently disable a rule)

Usage:
    from web.compliance import run_compliance_scan
    report = run_compliance_scan(device_serial="abc123")
"""

import json
import logging
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

REPORT_PATH = Path.home() / ".osmosis" / "compliance-report.json"


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

@dataclass
class ComplianceRule:
    """A single compliance rule — the atomic unit of the engine."""

    id: str  # e.g. "S01", "E01", "B01"
    name: str
    description: str
    severity: str  # minimal, standard, hardened
    category: str  # boot, encryption, network, baseband, app, auth, update
    tags: list[str] = field(default_factory=list)
    reference: str = ""  # external doc link or standard ref
    architectures: list[str] = field(
        default_factory=list
    )  # arm64, armv7, x86_64 — empty = all


@dataclass
class RuleResult:
    """Result of checking a single rule on a device."""

    rule_id: str
    rule_name: str
    enabled: bool
    passed: bool | None  # None = could not check
    detail: str
    severity: str
    category: str
    exclusion_reason: str = ""  # why it was skipped, if disabled


@dataclass
class ComplianceReport:
    """Full compliance report for a device."""

    schema_version: str = "org.osmosis.compliance.v1"
    scanned_at: str = ""
    device_serial: str = ""
    device_model: str = ""
    device_arch: str = ""
    target_level: str = "standard"
    total_rules: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    unchecked: int = 0
    results: list[dict] = field(default_factory=list)
    exceptions: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Severity levels (ordered)
# ---------------------------------------------------------------------------

SEVERITY_LEVELS = {"minimal": 0, "standard": 1, "hardened": 2}


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

_RULES: dict[str, ComplianceRule] = {}
_CHECK_FNS: dict[str, object] = {}


def register_rule(rule: ComplianceRule, check_fn):
    """Register a rule and its check function.

    check_fn signature: (serial: str | None, arch: str) -> RuleResult
    The check function receives the device serial (for ADB/fastboot queries)
    and architecture string.  It must return a RuleResult.
    """
    _RULES[rule.id] = rule
    _CHECK_FNS[rule.id] = check_fn


def get_all_rules() -> dict[str, ComplianceRule]:
    return dict(_RULES)


# ---------------------------------------------------------------------------
# ADB / device helpers
# ---------------------------------------------------------------------------


def _adb(serial: str | None, *args: str, timeout: int = 10) -> str | None:
    """Run an ADB command, return stdout or None on failure."""
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def _getprop(serial: str | None, prop: str) -> str | None:
    """Read an Android system property via ADB."""
    return _adb(serial, "shell", "getprop", prop)


def _shell(serial: str | None, cmd: str) -> str | None:
    """Run a shell command on device via ADB."""
    return _adb(serial, "shell", cmd)


def _detect_device(serial: str | None) -> tuple[str, str]:
    """Detect device model and architecture."""
    model = _getprop(serial, "ro.product.model") or "unknown"
    arch = _getprop(serial, "ro.product.cpu.abi") or "unknown"
    return model, arch


# ---------------------------------------------------------------------------
# Compliance engine
# ---------------------------------------------------------------------------


def _should_enable_rule(
    rule: ComplianceRule,
    target_level: str,
    excludes: list[str],
    exceptions: dict[str, str],
    device_arch: str,
) -> tuple[bool, str]:
    """Determine if a rule should be enabled.  Returns (enabled, reason)."""
    # Tag exclusion
    for tag in rule.tags:
        if tag in excludes:
            return False, f"excluded by tag '{tag}'"

    # Architecture mismatch
    if rule.architectures and device_arch not in rule.architectures:
        return False, (
            f"architecture '{device_arch}' not in {rule.architectures}"
        )

    # Severity level too high
    rule_level = SEVERITY_LEVELS.get(rule.severity, 0)
    target = SEVERITY_LEVELS.get(target_level, 1)
    if rule_level > target:
        return False, (
            f"severity '{rule.severity}' exceeds target '{target_level}'"
        )

    # Explicit exception (must have rationale)
    if rule.id in exceptions:
        rationale = exceptions[rule.id]
        return False, f"exception: {rationale}"

    return True, ""


def run_compliance_scan(
    device_serial: str | None = None,
    target_level: str = "standard",
    excludes: list[str] | None = None,
    exceptions: dict[str, str] | None = None,
) -> dict:
    """Run all registered rules against a connected device.

    Args:
        device_serial: ADB serial (None = use default device).
        target_level: minimal, standard, or hardened.
        excludes: list of tags to skip (e.g. ["baseband", "no-ipv6"]).
        exceptions: dict of rule_id -> rationale for explicit exclusions.

    Returns:
        Compliance report as a dict.
    """
    excludes = excludes or []
    exceptions = exceptions or {}

    model, arch = _detect_device(device_serial)
    results: list[RuleResult] = []

    for rule_id, rule in _RULES.items():
        enabled, reason = _should_enable_rule(
            rule, target_level, excludes, exceptions, arch
        )

        if not enabled:
            results.append(
                RuleResult(
                    rule_id=rule_id,
                    rule_name=rule.name,
                    enabled=False,
                    passed=None,
                    detail=f"Skipped: {reason}",
                    severity=rule.severity,
                    category=rule.category,
                    exclusion_reason=reason,
                )
            )
            continue

        # Run the check
        check_fn = _CHECK_FNS[rule_id]
        try:
            result = check_fn(device_serial, arch)
            results.append(result)
        except Exception as e:
            log.error("Rule %s check failed: %s", rule_id, e)
            results.append(
                RuleResult(
                    rule_id=rule_id,
                    rule_name=rule.name,
                    enabled=True,
                    passed=None,
                    detail=f"Check error: {e}",
                    severity=rule.severity,
                    category=rule.category,
                )
            )

    # Build report
    passed = sum(1 for r in results if r.passed is True)
    failed = sum(1 for r in results if r.passed is False)
    skipped = sum(1 for r in results if not r.enabled)
    unchecked = sum(
        1 for r in results if r.enabled and r.passed is None
    )

    report = ComplianceReport(
        scanned_at=datetime.now(timezone.utc).isoformat(),
        device_serial=device_serial or "default",
        device_model=model,
        device_arch=arch,
        target_level=target_level,
        total_rules=len(results),
        passed=passed,
        failed=failed,
        skipped=skipped,
        unchecked=unchecked,
        results=[asdict(r) for r in results],
        exceptions=exceptions,
    )

    report_dict = asdict(report)

    # Persist
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report_dict, indent=2) + "\n")

    return report_dict


def get_last_report() -> dict | None:
    """Load the most recent compliance report."""
    if not REPORT_PATH.exists():
        return None
    try:
        return json.loads(REPORT_PATH.read_text())
    except Exception:
        return None
