#!/usr/bin/env python3
"""
Osmosis Web UI — local Flask app for device flashing.
Runs on http://localhost:5000 and calls heimdall/adb/BLE tools under the hood.

Supports two frontends:
  - Legacy: Jinja2 template at /legacy (web/templates/index.html + web/static/)
  - Vue 3:  Vite build served from web/static/dist/ (default at /)

During development, run `npm run dev` in frontend/ (port 5173) which proxies
API calls to Flask on port 5000.
"""

import json
import os
from pathlib import Path

from flask import Flask, render_template, send_from_directory

from web.routes import bootable, cfw, device, flash, ipfs, os_builder, romfinder, safety, scooter, system, workflow

app = Flask(__name__)

# Register blueprints
app.register_blueprint(bootable.bp)
app.register_blueprint(cfw.bp)
app.register_blueprint(device.bp)
app.register_blueprint(flash.bp)
app.register_blueprint(ipfs.bp)
app.register_blueprint(os_builder.bp)
app.register_blueprint(romfinder.bp)
app.register_blueprint(system.bp)
app.register_blueprint(safety.bp)
app.register_blueprint(scooter.bp)
app.register_blueprint(workflow.bp)

# Path to Vite build output
DIST_DIR = Path(__file__).resolve().parent / "static" / "dist"


def _vue_assets() -> str:
    """Read the Vite manifest and return <script>/<link> tags for the entry point."""
    manifest_path = DIST_DIR / ".vite" / "manifest.json"
    if not manifest_path.exists():
        # Fallback: try older manifest location
        manifest_path = DIST_DIR / "manifest.json"
    if not manifest_path.exists():
        return "<!-- Vite build not found. Run: cd frontend && npm run build -->"

    manifest = json.loads(manifest_path.read_text())
    entry = manifest.get("src/main.js") or manifest.get("index.html") or {}
    tags = []

    # CSS
    for css in entry.get("css", []):
        tags.append(f'<link rel="stylesheet" href="/static/dist/{css}">')

    # JS entry
    js_file = entry.get("file", "")
    if js_file:
        tags.append(f'<script type="module" src="/static/dist/{js_file}"></script>')

    return "\n    ".join(tags)


@app.route("/")
def index_vue():
    """Serve the Vue 3 SPA (production build)."""
    # If dist exists, serve the Vue app; otherwise fall back to legacy
    if (DIST_DIR / "index.html").exists():
        return send_from_directory(str(DIST_DIR), "index.html")
    if (DIST_DIR / ".vite").exists() or (DIST_DIR / "manifest.json").exists():
        return render_template("vue.html", assets=_vue_assets())
    # Fallback to legacy template
    return render_template("index.html")


@app.route("/legacy")
def index_legacy():
    """Serve the original Jinja2 template (legacy frontend)."""
    return render_template("index.html")


@app.route("/static/dist/<path:filename>")
def vue_static(filename):
    """Serve Vite build assets."""
    return send_from_directory(str(DIST_DIR), filename)


if __name__ == "__main__":
    import webbrowser

    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Osmosis Web UI: http://localhost:{port}")
    print(f"  Legacy UI:      http://localhost:{port}/legacy")
    print(f"  Dev frontend:   http://localhost:5173 (run: cd frontend && npm run dev)\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
