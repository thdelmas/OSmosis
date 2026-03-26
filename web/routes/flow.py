"""Universal flow API routes."""

from flask import Blueprint, jsonify, request

from web.flow_engine import FlowEngine
from web.flow_loader import find_flows, get_flow

bp = Blueprint("flow", __name__)
_engine = FlowEngine()


@bp.route("/api/flows")
def api_flows():
    """List available flows, optionally filtered.

    Query params: ?category=phone&brand=xiaomi&mode=sideload
    """
    category = request.args.get("category", "")
    brand = request.args.get("brand", "")
    mode = request.args.get("mode", "")

    flows = find_flows(category=category, brand=brand, mode=mode)
    return jsonify({"flows": flows})


@bp.route("/api/flows/<flow_id>")
def api_flow_detail(flow_id: str):
    """Get a flow definition (metadata only)."""
    flow = get_flow(flow_id)
    if not flow:
        return jsonify({"error": f"Flow '{flow_id}' not found"}), 404

    return jsonify(
        {
            "id": flow["id"],
            "name": flow.get("name", ""),
            "description": flow.get("description", ""),
            "category": flow.get("category", ""),
            "brands": flow.get("brands", []),
            "step_count": len(flow.get("steps", [])),
        }
    )


@bp.route("/api/flow/evaluate", methods=["POST"])
def api_flow_evaluate():
    """Evaluate a flow against the given context.

    Expected JSON body::

        {
            "flow_id": "xiaomi-recovery",
            "context": {
                "mode": "fastboot",
                "bl_locked": true,
                "hw_codename": "courbet",
                "fw_codename": "renoir",
                "path_chosen": "unlock_flash",
                ...
            }
        }

    Returns the resolved step tree with statuses, blocking reasons,
    diagnosis, warnings, and recommendation.
    """
    body = request.json or {}
    flow_id = body.get("flow_id", "")
    context = body.get("context", {})

    flow = get_flow(flow_id)
    if not flow:
        return jsonify({"error": f"Flow '{flow_id}' not found"}), 404

    result = _engine.evaluate(flow, context)
    return jsonify(result)
