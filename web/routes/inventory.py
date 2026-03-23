"""API routes for the dynamic device inventory."""

from flask import Blueprint, jsonify

bp = Blueprint("inventory", __name__)


@bp.route("/api/inventory")
def api_inventory():
    """Scan and return all detected devices across USB, ADB, serial, and network."""
    from web.inventory import inventory_to_dicts, scan_inventory

    devices = scan_inventory()
    return jsonify(inventory_to_dicts(devices))


@bp.route("/api/inventory/usb")
def api_inventory_usb():
    """Scan USB devices only."""
    from web.inventory import _detect_usb, inventory_to_dicts

    return jsonify(inventory_to_dicts(_detect_usb()))


@bp.route("/api/inventory/adb")
def api_inventory_adb():
    """Scan ADB devices only."""
    from web.inventory import _detect_adb, inventory_to_dicts

    return jsonify(inventory_to_dicts(_detect_adb()))


@bp.route("/api/inventory/serial")
def api_inventory_serial():
    """Scan serial port devices only."""
    from web.inventory import _detect_serial, inventory_to_dicts

    return jsonify(inventory_to_dicts(_detect_serial()))


@bp.route("/api/inventory/network")
def api_inventory_network():
    """Scan network devices via mDNS."""
    from web.inventory import _detect_network, inventory_to_dicts

    return jsonify(inventory_to_dicts(_detect_network()))
