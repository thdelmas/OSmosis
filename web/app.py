#!/usr/bin/env python3
"""
Osmosis Web UI — local Flask app for device flashing.
Runs on http://localhost:5000 and calls heimdall/adb/BLE tools under the hood.

Frontend: Vue 3 SPA built with Vite, served from web/static/dist/.
During development, run `npm run dev` in frontend/ (port 5173) which proxies
API calls to Flask on port 5000.
"""

import os
from pathlib import Path

from flask import Flask, send_from_directory

from web.plugin import discover_plugins
from web.routes import (
    bootable,
    cfw,
    console,
    device,
    device_migration,
    device_os,
    device_submissions,
    diagnostics,
    ebike,
    ereader,
    esp_firmware,
    fastboot,
    firmware,
    flash,
    integrity,
    inventory,
    ipfs,
    ipfs_config,
    keyboard,
    lab_equipment,
    medicat,
    microcontroller,
    os_builder,
    os_builder_gallery,
    profiles,
    romfinder,
    router,
    safety,
    scooter,
    scooter_ota,
    sdr,
    search,
    synth,
    system,
    t2,
    vacuum,
    workflow,
    workflow_update,
)
from web.routes import (
    plugin as plugin_routes,
)
from web.security import init_security

app = Flask(__name__)

# Register blueprints
app.register_blueprint(bootable.bp)
app.register_blueprint(cfw.bp)
app.register_blueprint(console.bp)
app.register_blueprint(device.bp)
app.register_blueprint(device_migration.bp)
app.register_blueprint(device_os.bp)
app.register_blueprint(device_submissions.bp)
app.register_blueprint(diagnostics.bp)
app.register_blueprint(ebike.bp)
app.register_blueprint(fastboot.bp)
app.register_blueprint(firmware.bp)
app.register_blueprint(flash.bp)
app.register_blueprint(keyboard.bp)
app.register_blueprint(lab_equipment.bp)
app.register_blueprint(ipfs.bp)
app.register_blueprint(ipfs_config.bp)
app.register_blueprint(medicat.bp)
app.register_blueprint(microcontroller.bp)
app.register_blueprint(ereader.bp)
app.register_blueprint(esp_firmware.bp)
app.register_blueprint(os_builder.bp)
app.register_blueprint(os_builder_gallery.bp)
app.register_blueprint(romfinder.bp)
app.register_blueprint(router.bp)
app.register_blueprint(search.bp)
app.register_blueprint(system.bp)
app.register_blueprint(plugin_routes.bp)
app.register_blueprint(safety.bp)
app.register_blueprint(sdr.bp)
app.register_blueprint(synth.bp)
app.register_blueprint(vacuum.bp)
app.register_blueprint(t2.bp)
app.register_blueprint(scooter.bp)
app.register_blueprint(scooter_ota.bp)
app.register_blueprint(workflow.bp)
app.register_blueprint(workflow_update.bp)
app.register_blueprint(profiles.bp)
app.register_blueprint(integrity.bp)
app.register_blueprint(inventory.bp)

# Discover device driver plugins
discover_plugins()

# Security: rate limiting + optional token auth
init_security(app)

# Path to Vite build output
DIST_DIR = Path(__file__).resolve().parent / "static" / "dist"


@app.route("/")
def index():
    """Serve the Vue 3 SPA."""
    if (DIST_DIR / "index.html").exists():
        return send_from_directory(str(DIST_DIR), "index.html")
    return "Frontend not built. Run: cd frontend && npm run build", 500


@app.route("/static/dist/<path:filename>")
def vue_static(filename):
    """Serve Vite build assets."""
    return send_from_directory(str(DIST_DIR), filename)


if __name__ == "__main__":
    import webbrowser

    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Osmosis Web UI: http://localhost:{port}")
    print("  Dev frontend:   http://localhost:5173 (run: cd frontend && npm run dev)\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=os.environ.get("FLASK_DEBUG", "1") == "1")  # noqa: S201
