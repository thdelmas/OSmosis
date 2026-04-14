"""API routes for device compliance scanning and reporting."""

from flask import Blueprint, jsonify, request

bp = Blueprint("compliance", __name__)


@bp.route("/api/compliance/rules")
def api_compliance_rules():
    """List all registered compliance rules and their metadata."""
    from web.compliance import get_all_rules

    rules = get_all_rules()
    return jsonify(
        {
            "total": len(rules),
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity,
                    "category": r.category,
                    "tags": r.tags,
                    "reference": r.reference,
                }
                for r in rules.values()
            ],
        }
    )


@bp.route("/api/compliance/scan", methods=["POST"])
def api_compliance_scan():
    """Run a compliance scan on a connected device.

    JSON body (all optional):
        serial:       ADB device serial (null = default device)
        level:        "minimal", "standard", or "hardened" (default: standard)
        excludes:     list of tags to skip, e.g. ["baseband"]
        exceptions:   dict of rule_id -> rationale, e.g. {"B02": "Custom ROM"}
    """
    # Import here to trigger rule auto-registration on first use
    import web.compliance_rules  # noqa: F401
    from web.compliance import run_compliance_scan

    data = request.get_json(silent=True) or {}
    report = run_compliance_scan(
        device_serial=data.get("serial"),
        target_level=data.get("level", "standard"),
        excludes=data.get("excludes", []),
        exceptions=data.get("exceptions", {}),
    )
    return jsonify(report)


@bp.route("/api/compliance/report")
def api_compliance_report():
    """Get the most recent compliance report."""
    from web.compliance import get_last_report

    report = get_last_report()
    if not report:
        return jsonify(
            {"error": "No compliance report found. Run a scan first."}
        ), 404
    return jsonify(report)


@bp.route("/api/compliance/summary")
def api_compliance_summary():
    """Get a compact summary of the latest compliance scan.

    Useful for dashboard badges and quick status checks.
    """
    from web.compliance import get_last_report

    report = get_last_report()
    if not report:
        return jsonify({"scanned": False})

    failed = [
        {"id": r["rule_id"], "name": r["rule_name"], "detail": r["detail"]}
        for r in report.get("results", [])
        if r.get("passed") is False
    ]
    return jsonify(
        {
            "scanned": True,
            "scanned_at": report.get("scanned_at", ""),
            "device_model": report.get("device_model", ""),
            "target_level": report.get("target_level", ""),
            "passed": report.get("passed", 0),
            "failed": report.get("failed", 0),
            "skipped": report.get("skipped", 0),
            "total": report.get("total_rules", 0),
            "failed_rules": failed,
        }
    )
