"""Community links and ROM changelog routes."""

import json
import re
import subprocess

from flask import Blueprint, jsonify, request

bp = Blueprint("romfinder_community", __name__)


@bp.route("/api/community/<codename>")
def api_community(codename):
    """Return community links for a given device codename."""
    codename = codename.strip().lower()
    model = request.args.get("model", "").strip()
    search_term = model or codename

    links = [
        {
            "id": "xda",
            "name": "XDA Forums",
            "icon": "forum",
            "url": (
                f"https://xdaforums.com/search/?q={search_term}+ROM&type=post"
            ),
            "desc": (
                "Community forums for custom ROMs, mods, and troubleshooting"
            ),
        },
    ]

    try:
        r = subprocess.run(
            [
                "curl",
                "-sL",
                "--max-time",
                "6",
                f"https://xdaforums.com/search/?q={search_term}&type=post",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        forum_match = re.search(
            rf'href="(https://xdaforums\.com/[ct]/[^"]*'
            rf"{re.escape(codename)}"
            rf'[^"]*)"',
            r.stdout,
            re.IGNORECASE,
        )
        if forum_match:
            links[0]["device_url"] = forum_match.group(1)
    except Exception:
        pass

    links.extend(
        [
            {
                "id": "lineageos_wiki",
                "name": "LineageOS Wiki",
                "icon": "wiki",
                "url": (f"https://wiki.lineageos.org/devices/{codename}"),
                "desc": "Official install guides and device info",
            },
            {
                "id": "pmos_wiki",
                "name": "postmarketOS Wiki",
                "icon": "wiki",
                "url": (
                    f"https://wiki.postmarketos.org/wiki/"
                    f"Special:Search?search={search_term}"
                ),
                "desc": "Linux on mobile devices",
            },
            {
                "id": "ubports",
                "name": "Ubuntu Touch",
                "icon": "device",
                "url": "https://devices.ubuntu-touch.io/",
                "desc": "Ubuntu Touch device compatibility",
            },
            {
                "id": "ifixit",
                "name": "iFixit",
                "icon": "repair",
                "url": (f"https://www.ifixit.com/Search?query={search_term}"),
                "desc": "Repair guides and teardowns",
            },
            {
                "id": "gsmarena",
                "name": "GSMArena",
                "icon": "specs",
                "url": (
                    f"https://www.gsmarena.com/results.php3"
                    f"?sQuickSearch=yes&sName={search_term}"
                ),
                "desc": "Detailed device specifications",
            },
        ]
    )

    if model and model.upper().startswith("SM-"):
        links.append(
            {
                "id": "sammobile",
                "name": "SamMobile",
                "icon": "firmware",
                "url": (f"https://www.sammobile.com/firmwares/?q={model}"),
                "desc": "Samsung firmware database",
            }
        )

    return jsonify({"codename": codename, "model": model, "links": links})


@bp.route("/api/changelog/<codename>")
def api_changelog(codename):
    """Get changelogs and version history for available ROMs."""
    codename = codename.strip().lower()
    model = request.args.get("model", "").strip()
    installed_version = request.args.get("installed", "").strip()
    changelogs = []

    # --- LineageOS ---
    for name in [codename, model.lower()] if model else [codename]:
        if not name:
            continue
        try:
            r = subprocess.run(
                [
                    "curl",
                    "-sL",
                    "--max-time",
                    "8",
                    f"https://download.lineageos.org"
                    f"/api/v2/devices/{name}/builds",
                ],
                capture_output=True,
                text=True,
                timeout=12,
            )
            builds = (
                json.loads(r.stdout) if r.stdout.strip().startswith("[") else []
            )
            if builds and isinstance(builds, list):
                entries = _parse_lineageos_builds(builds, name)
                changelogs.append(
                    _changelog_entry(
                        "lineageos",
                        "LineageOS",
                        entries,
                        installed_version,
                    )
                )
                break
        except Exception:
            pass

    # --- /e/OS ---
    for name in [codename, model.lower()] if model else [codename]:
        if not name:
            continue
        try:
            r = subprocess.run(
                [
                    "curl",
                    "-sL",
                    "--max-time",
                    "8",
                    f"https://images.ecloud.global/stable/{name}/",
                ],
                capture_output=True,
                text=True,
                timeout=12,
            )
            if r.returncode == 0 and "Not Found" not in r.stdout:
                entries = _parse_eos_builds(r.stdout, name)
                if entries:
                    changelogs.append(
                        _changelog_entry(
                            "eos",
                            "/e/OS",
                            entries,
                            installed_version,
                        )
                    )
                    break
        except Exception:
            pass

    return jsonify({"codename": codename, "changelogs": changelogs})


def _parse_lineageos_builds(builds, name):
    entries = []
    for b in builds[:10]:
        entry = {
            "version": b.get("version", ""),
            "date": b.get("datetime", ""),
            "filename": b.get("filename", ""),
            "size": b.get("size", 0),
            "download_url": "",
        }
        if entry["filename"]:
            entry["download_url"] = (
                f"https://mirrorbits.lineageos.org"
                f"/full/{name}/{entry['filename']}"
            )
        if isinstance(entry["date"], (int, float)):
            from datetime import datetime as dt

            entry["date"] = dt.fromtimestamp(entry["date"]).strftime("%Y-%m-%d")
        entries.append(entry)
    return entries


def _parse_eos_builds(html, name):
    eos_builds = re.findall(r'href="(e-[\d.]+-[^"]+\.zip)"', html)
    if not eos_builds:
        return []
    entries = []
    for fname in reversed(eos_builds[-10:]):
        m = re.search(r"e-([\d.]+)-", fname)
        entries.append(
            {
                "version": m.group(1) if m else "",
                "date": "",
                "filename": fname,
                "size": 0,
                "download_url": (
                    f"https://images.ecloud.global/stable/{name}/{fname}"
                ),
            }
        )
    entries.reverse()
    return entries


def _changelog_entry(rom_id, rom_name, entries, installed):
    return {
        "rom_id": rom_id,
        "rom_name": rom_name,
        "builds": entries,
        "installed": installed,
        "latest": entries[0]["version"] if entries else "",
        "update_available": bool(
            installed and entries and entries[0]["version"] != installed
        ),
    }
