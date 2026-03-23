"""Config migration routes (pipe-delimited -> YAML)."""

from flask import Blueprint, jsonify

bp = Blueprint("device_migration", __name__)


@bp.route("/api/devices/migrate-yaml", methods=["POST"])
def api_devices_migrate_yaml():
    """Migrate pipe-delimited .cfg files to structured YAML.

    This creates .yaml files alongside the existing .cfg files.
    The .cfg files are preserved as backups.
    """
    import yaml

    from web.core import (
        CONFIG_FILE,
        DEVICES_YAML,
        MCU_CONFIG_FILE,
        MCU_YAML,
        SCRIPT_DIR,
        parse_devices_cfg,
        parse_microcontrollers_cfg,
    )

    migrated = []

    # Devices
    if CONFIG_FILE.exists() and not DEVICES_YAML.exists():
        devices = parse_devices_cfg()
        if devices:
            DEVICES_YAML.write_text(yaml.dump(devices, default_flow_style=False, sort_keys=False))
            migrated.append("devices.yaml")

    # Microcontrollers
    if MCU_CONFIG_FILE.exists() and not MCU_YAML.exists():
        boards = parse_microcontrollers_cfg()
        if boards:
            MCU_YAML.write_text(yaml.dump(boards, default_flow_style=False, sort_keys=False))
            migrated.append("microcontrollers.yaml")

    # Scooters
    scooters_cfg = SCRIPT_DIR / "scooters.cfg"
    scooters_yaml = SCRIPT_DIR / "scooters.yaml"
    if scooters_cfg.exists() and not scooters_yaml.exists():
        from web.routes.scooter import parse_scooters_cfg

        scooters = parse_scooters_cfg()
        if scooters:
            scooters_yaml.write_text(yaml.dump(scooters, default_flow_style=False, sort_keys=False))
            migrated.append("scooters.yaml")

    # E-bikes
    ebikes_cfg = SCRIPT_DIR / "ebikes.cfg"
    ebikes_yaml = SCRIPT_DIR / "ebikes.yaml"
    if ebikes_cfg.exists() and not ebikes_yaml.exists():
        from web.routes.ebike import parse_ebikes_cfg

        ebikes = parse_ebikes_cfg()
        if ebikes:
            ebikes_yaml.write_text(yaml.dump(ebikes, default_flow_style=False, sort_keys=False))
            migrated.append("ebikes.yaml")

    if not migrated:
        return jsonify({"message": "Nothing to migrate (YAML files already exist or no .cfg files found)"})

    return jsonify({"migrated": migrated})
