"""Plugin management routes."""

from flask import Blueprint, jsonify

bp = Blueprint("plugin_routes", __name__)


@bp.route("/api/plugins")
def api_plugins():
    """List all registered device driver plugins."""
    from web.plugin import list_plugins

    return jsonify(
        [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "version": p.version,
                "capabilities": p.capabilities,
            }
            for p in list_plugins()
        ]
    )


@bp.route("/api/plugins/detect/<plugin_id>")
def api_plugin_detect(plugin_id: str):
    """Run device detection using a specific plugin."""
    from web.plugin import get_driver

    driver = get_driver(plugin_id)
    if not driver:
        return jsonify({"error": f"Plugin '{plugin_id}' not found"}), 404
    try:
        devices = driver.detect()
        return jsonify({"plugin": plugin_id, "devices": devices})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plugins/info/<plugin_id>/<device_id>")
def api_plugin_info(plugin_id: str, device_id: str):
    """Read device info using a specific plugin."""
    from web.plugin import get_driver

    driver = get_driver(plugin_id)
    if not driver:
        return jsonify({"error": f"Plugin '{plugin_id}' not found"}), 404
    try:
        info = driver.info(device_id)
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
