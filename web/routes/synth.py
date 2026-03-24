"""Synthesizer and audio device routes — firmware update for Eurorack modules.

Supports Mutable Instruments (WAV bootloader), Korg logue SDK, and
MOD Dwarf/Duo plugin management.
"""

from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, cmd_exists, start_task

bp = Blueprint("synth", __name__)

# Known synth module audio bootloader patterns
_SYNTH_MODULES = {
    "mi-plaits": {
        "name": "Mutable Instruments Plaits",
        "brand": "Mutable Instruments",
        "method": "wav",
        "desc": "Macro oscillator. Flash via WAV file played into audio input.",
    },
    "mi-rings": {
        "name": "Mutable Instruments Rings",
        "brand": "Mutable Instruments",
        "method": "wav",
        "desc": "Resonator. Flash via WAV file played into audio input.",
    },
    "mi-clouds": {
        "name": "Mutable Instruments Clouds",
        "brand": "Mutable Instruments",
        "method": "wav",
        "desc": "Granular processor. Flash via WAV file played into audio input.",
    },
    "mi-braids": {
        "name": "Mutable Instruments Braids",
        "brand": "Mutable Instruments",
        "method": "wav",
        "desc": "Digital oscillator. Flash via WAV file played into audio input.",
    },
    "mi-marbles": {
        "name": "Mutable Instruments Marbles",
        "brand": "Mutable Instruments",
        "method": "wav",
        "desc": "Random sampler. Flash via WAV file played into audio input.",
    },
    "mi-stages": {
        "name": "Mutable Instruments Stages",
        "brand": "Mutable Instruments",
        "method": "wav",
        "desc": "Segment generator. Flash via WAV file played into audio input.",
    },
    "mi-beads": {
        "name": "Mutable Instruments Beads",
        "brand": "Mutable Instruments",
        "method": "wav",
        "desc": "Granular processor (Clouds successor). Flash via WAV.",
    },
    "korg-prologue": {
        "name": "Korg Prologue",
        "brand": "Korg",
        "method": "sound-librarian",
        "desc": "Custom oscillators via Korg Sound Librarian or logue SDK.",
    },
    "korg-minilogue-xd": {
        "name": "Korg Minilogue XD",
        "brand": "Korg",
        "method": "sound-librarian",
        "desc": "Custom oscillators and effects via Sound Librarian.",
    },
}


@bp.route("/api/synth/modules")
def api_synth_modules():
    """Return all known synthesizer modules with firmware info."""
    brand = request.args.get("brand", "").lower().strip()
    modules = []
    for module_id, info in _SYNTH_MODULES.items():
        if brand and brand not in info["brand"].lower():
            continue
        modules.append({"id": module_id, **info})
    return jsonify(modules)


@bp.route("/api/synth/flash-guide/<module_id>")
def api_synth_flash_guide(module_id):
    """Return flash instructions for a specific synth module."""
    info = _SYNTH_MODULES.get(module_id)
    if not info:
        return jsonify({"error": f"Unknown module: {module_id}"}), 404

    steps = []

    if info["method"] == "wav":
        steps = [
            {
                "id": "download",
                "title": "Download the firmware WAV file",
                "desc": f"Get the latest firmware for {info['name']} from the "
                "Mutable Instruments GitHub releases or the module's firmware page.",
            },
            {
                "id": "bootloader",
                "title": "Enter bootloader mode",
                "desc": "Power on your Eurorack case while holding the module's "
                "encoder or button (varies by module). The module's LEDs will "
                "show a distinctive pattern indicating bootloader mode.",
            },
            {
                "id": "play-wav",
                "title": "Play the WAV file into the audio input",
                "desc": "Connect your computer's headphone output to the module's "
                "audio input (usually IN L). Play the firmware WAV file at "
                "**maximum volume** with no EQ or effects. The module's LEDs "
                "will animate during the transfer. Do not interrupt playback.",
            },
            {
                "id": "verify",
                "title": "Verify and reboot",
                "desc": "After playback completes, the module will verify the "
                "firmware and reboot automatically. If the LEDs show an error "
                "pattern, try again with a different audio cable or adjust volume.",
            },
        ]
    elif info["method"] == "sound-librarian":
        steps = [
            {
                "id": "install",
                "title": "Install Korg Sound Librarian",
                "desc": "Download Sound Librarian from the Korg website for your operating system.",
            },
            {
                "id": "connect",
                "title": "Connect via USB",
                "desc": f"Connect your {info['name']} to your computer via USB.",
            },
            {
                "id": "upload",
                "title": "Upload custom oscillators/effects",
                "desc": "Use Sound Librarian to transfer custom oscillator or "
                "effect .mnlgxdunit files to the synth's user slots.",
            },
        ]

    return jsonify(
        {
            "module": module_id,
            "name": info["name"],
            "method": info["method"],
            "steps": steps,
        }
    )


@bp.route("/api/synth/play-firmware", methods=["POST"])
def api_play_firmware():
    """Play a firmware WAV file through the default audio output.

    JSON body: { "wav_path": "/path/to/firmware.wav" }

    Uses aplay (ALSA) or paplay (PulseAudio) to play the WAV file.
    The user should have the module in bootloader mode and connected
    via audio cable before calling this.
    """
    body = request.json or {}
    wav_path = body.get("wav_path", "").strip()

    if not wav_path or not Path(wav_path).is_file():
        return jsonify({"error": "WAV file not found"}), 400

    if not wav_path.lower().endswith(".wav"):
        return jsonify({"error": "File must be a .wav file"}), 400

    player = None
    if cmd_exists("aplay"):
        player = "aplay"
    elif cmd_exists("paplay"):
        player = "paplay"
    else:
        return jsonify({"error": "No audio player found (need aplay or paplay)"}), 500

    def _run(task: Task):
        task.emit(f"Playing firmware WAV via {player}...", "info")
        task.emit("Do NOT interrupt playback or disconnect the audio cable.", "warn")
        task.emit(f"File: {wav_path}", "info")

        rc = task.run_shell([player, wav_path])

        if rc == 0:
            task.emit(
                "Playback complete. The module should verify and reboot.",
                "success",
            )
        else:
            task.emit("Playback failed. Check audio output settings.", "error")
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id})
