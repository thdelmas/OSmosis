#!/usr/bin/env python3
"""
Osmosis Web UI — local Flask app for Samsung device flashing.
Runs on http://localhost:5000 and calls heimdall/adb under the hood.
"""

import os

from flask import Flask, render_template

from web.routes import bootable, device, flash, ipfs, romfinder, system, workflow

app = Flask(__name__)

# Register blueprints
app.register_blueprint(bootable.bp)
app.register_blueprint(device.bp)
app.register_blueprint(flash.bp)
app.register_blueprint(ipfs.bp)
app.register_blueprint(romfinder.bp)
app.register_blueprint(system.bp)
app.register_blueprint(workflow.bp)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    import webbrowser

    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Osmosis Web UI: http://localhost:{port}\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
