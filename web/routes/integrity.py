"""API routes for firmware integrity monitoring and privilege audit log."""

from flask import Blueprint, jsonify, request

bp = Blueprint("integrity", __name__)


@bp.route("/api/integrity/check", methods=["POST"])
def api_integrity_check():
    """Run a firmware integrity scan now.

    Scans all cached firmware files and verifies checksums against
    the registry and previous scans. Returns the full report.
    """
    from web.integrity import check_integrity

    report = check_integrity()
    return jsonify(report)


@bp.route("/api/integrity/report")
def api_integrity_report():
    """Get the most recent integrity report (from last scan)."""
    from web.integrity import get_last_report

    report = get_last_report()
    if not report:
        return jsonify(
            {"error": "No integrity report found. Run a scan first."}
        ), 404
    return jsonify(report)


@bp.route("/api/integrity/alerts")
def api_integrity_alerts():
    """Get just the tampered/error entries from the latest report.

    Used by the UI to show a warning banner.
    """
    from web.integrity import get_last_report

    report = get_last_report()
    if not report:
        return jsonify({"alerts": [], "all_clear": True})

    alerts = []
    results = report.get("results", {})
    for item in results.get("tampered", []):
        alerts.append(
            {
                "type": "tampered",
                "path": item["path"],
                "message": f"File modified since last scan: {item['path']}",
                "status": item.get("status", "tampered"),
            }
        )
    for item in results.get("errors", []):
        alerts.append(
            {
                "type": "error",
                "path": item["path"],
                "message": f"Error checking {item['path']}: {item.get('error', 'unknown')}",
            }
        )

    return jsonify(
        {
            "alerts": alerts,
            "all_clear": len(alerts) == 0,
            "scanned_at": report.get("scanned_at", ""),
        }
    )


@bp.route("/api/audit-log")
def api_audit_log():
    """Get recent privilege-escalated operations."""
    from web.integrity import get_audit_log

    limit = request.args.get("limit", "100")
    try:
        limit = int(limit)
    except ValueError:
        limit = 100

    entries = get_audit_log(limit=limit)
    return jsonify(entries)
