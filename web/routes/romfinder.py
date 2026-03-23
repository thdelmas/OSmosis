"""ROM finder, community links, and changelog routes."""

import json
import re
import subprocess
from pathlib import Path

from flask import Blueprint, jsonify, request

from web.core import Task, start_task
from web.ipfs_helpers import ipfs_available, ipfs_index_load, ipfs_index_lookup, ipfs_pin_and_index, verify_fetched_file

bp = Blueprint("romfinder", __name__)


@bp.route("/api/romfinder/<codename>")
def api_romfinder(codename):
    """Check which ROMs are available for a given device codename."""
    codename_raw = codename.strip()
    codename = codename_raw.lower()
    model = request.args.get("model", "").strip()
    results = []

    # --- LineageOS ---
    for name in [codename, model.lower()] if model else [codename]:
        if not name:
            continue
        try:
            r = subprocess.run(
                ["curl", "-sL", "--max-time", "8", f"https://download.lineageos.org/api/v2/devices/{name}/builds"],
                capture_output=True,
                text=True,
                timeout=12,
            )
            builds = json.loads(r.stdout) if r.stdout.strip().startswith("[") else []
            if builds and isinstance(builds, list) and len(builds) > 0:
                latest = builds[0]
                results.append(
                    {
                        "id": "lineageos",
                        "name": "LineageOS",
                        "version": latest.get("version", ""),
                        "filename": latest.get("filename", ""),
                        "file_size": latest.get("size", 0),
                        "download_url": f"https://mirrorbits.lineageos.org/full/{name}/{latest.get('filename', '')}"
                        if latest.get("filename")
                        else "",
                        "page_url": f"https://download.lineageos.org/devices/{name}/builds",
                    }
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
                ["curl", "-sL", "--max-time", "8", f"https://images.ecloud.global/stable/{name}/"],
                capture_output=True,
                text=True,
                timeout=12,
            )
            if r.returncode == 0 and "Not Found" not in r.stdout and name in r.stdout.lower():
                eos_builds = re.findall(r'href="(e-[\d.]+-[^"]+\.zip)"', r.stdout)
                latest = eos_builds[-1] if eos_builds else ""
                version = ""
                if latest:
                    m = re.search(r"e-([\d.]+)-", latest)
                    version = m.group(1) if m else ""
                results.append(
                    {
                        "id": "eos",
                        "name": "/e/OS",
                        "version": version,
                        "filename": latest,
                        "download_url": f"https://images.ecloud.global/stable/{name}/{latest}" if latest else "",
                        "page_url": f"https://doc.e.foundation/devices/{name}/install",
                    }
                )
                break
        except Exception:
            pass

    # --- TWRP ---
    # Search multiple brand pages on twrp.me, not just Samsung
    twrp_brands = ["Samsung", "Google", "OnePlus", "Xiaomi", "Motorola", "Sony", "LG", "Huawei", "Fairphone", "Asus"]
    twrp_found = False
    for twrp_brand in twrp_brands:
        if twrp_found:
            break
        try:
            r = subprocess.run(
                ["curl", "-sL", "--max-time", "6", f"https://twrp.me/Devices/{twrp_brand}/"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            brand_lower = twrp_brand.lower()
            pattern = rf'<a\s+href="(/{brand_lower}/[^"]+)">[^<]*\({codename}[^)]*\)</a>'
            m = re.search(pattern, r.stdout, re.IGNORECASE)
            if not m and model:
                model_pattern = rf'<a\s+href="(/{brand_lower}/[^"]+)">[^<]*{re.escape(model)}[^<]*</a>'
                m = re.search(model_pattern, r.stdout, re.IGNORECASE)
            if not m:
                # Broader codename match anywhere in the link text
                broad_pattern = rf'<a\s+href="(/{brand_lower}/[^"]+)">[^<]*{re.escape(codename)}[^<]*</a>'
                m = re.search(broad_pattern, r.stdout, re.IGNORECASE)
            if m:
                results.append(
                    {
                        "id": "twrp",
                        "name": "TWRP Recovery",
                        "version": "",
                        "filename": "",
                        "download_url": "",
                        "page_url": f"https://twrp.me{m.group(1)}",
                    }
                )
                twrp_found = True
        except Exception:
            pass

    # --- postmarketOS ---
    try:
        pmos_found = False
        pmos_device = f"samsung-{codename}"
        for channel in ["edge", "v24.12", "v24.06", "v23.12"]:
            if pmos_found:
                break
            try:
                r = subprocess.run(
                    ["curl", "-sL", "--max-time", "6", f"https://images.postmarketos.org/bpo/{channel}/{pmos_device}/"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if r.returncode == 0 and "404" not in r.stdout[:200] and pmos_device in r.stdout.lower():
                    imgs = re.findall(r'href="([^"]+\.img\.xz)"', r.stdout)
                    if imgs:
                        results.append(
                            {
                                "id": "postmarketos",
                                "name": "postmarketOS",
                                "version": channel,
                                "filename": imgs[-1],
                                "download_url": f"https://images.postmarketos.org/bpo/{channel}/{pmos_device}/{imgs[-1]}",
                                "page_url": f"https://images.postmarketos.org/bpo/{channel}/{pmos_device}/",
                            }
                        )
                        pmos_found = True
            except Exception:
                pass

        if not pmos_found:
            pmos_terms = [codename_raw] + ([model] if model else [])
            for pmos_term in pmos_terms:
                if pmos_found:
                    break
                r = subprocess.run(
                    [
                        "curl",
                        "-sL",
                        "--max-time",
                        "8",
                        f"https://wiki.postmarketos.org/api.php?action=query&list=search&srsearch={pmos_term}&format=json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=12,
                )
                if r.returncode == 0 and r.stdout.strip():
                    try:
                        search_data = json.loads(r.stdout)
                        for sr in search_data.get("query", {}).get("search", []):
                            title = sr.get("title", "")
                            if codename in title.lower() or (model and model.lower() in title.lower()):
                                results.append(
                                    {
                                        "id": "postmarketos",
                                        "name": "postmarketOS",
                                        "version": "pmbootstrap",
                                        "filename": "",
                                        "download_url": "",
                                        "page_url": f"https://wiki.postmarketos.org/wiki/{title.replace(' ', '_')}",
                                        "install_method": "pmbootstrap",
                                    }
                                )
                                pmos_found = True
                                break
                    except (json.JSONDecodeError, KeyError):
                        pass
    except Exception:
        pass

    # --- Replicant ---
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "8", "https://redmine.replicant.us/projects/replicant/wiki/ReplicantImages"],
            capture_output=True,
            text=True,
            timeout=12,
        )
        if r.returncode == 0:
            model_short = model.replace("GT-", "").lower() if model else ""
            search_terms = [codename] + ([model_short] if model_short else [])
            for term in search_terms:
                dl_match = re.search(
                    rf'href="(https://download\.replicant\.us/[^"]*/{re.escape(term)}/[^"]*\.zip)"',
                    r.stdout,
                    re.IGNORECASE,
                )
                if dl_match:
                    dl_url = dl_match.group(1)
                    filename = dl_url.rsplit("/", 1)[-1]
                    ver_m = re.search(r"replicant-([\d.]+-\d+)", filename)
                    rec_match = re.search(
                        rf'href="(https://download\.replicant\.us/[^"]*/{re.escape(term)}/recovery[^"]*\.img)"',
                        r.stdout,
                        re.IGNORECASE,
                    )
                    entry = {
                        "id": "replicant",
                        "name": "Replicant",
                        "version": ver_m.group(1) if ver_m else "",
                        "filename": filename,
                        "download_url": dl_url,
                        "page_url": "https://redmine.replicant.us/projects/replicant/wiki/ReplicantImages",
                    }
                    if rec_match:
                        entry["recovery_url"] = rec_match.group(1)
                        entry["required_recovery"] = {
                            "id": "replicant-recovery",
                            "name": "Replicant Recovery",
                            "desc": "Replicant's own recovery — required to install Replicant ROMs.",
                            "type": "recovery",
                            "tags": ["recovery"],
                            "url": rec_match.group(1),
                        }
                    results.append(entry)
                    break
    except Exception:
        pass

    # --- Search links ---
    search_term = model or codename_raw
    search_links = [
        {"id": "xda", "name": "XDA Forums", "url": f"https://xdaforums.com/search/?q={search_term}+ROM&type=post"},
        {"id": "lineageos_wiki", "name": "LineageOS Wiki", "url": "https://wiki.lineageos.org/devices/#samsung"},
        {
            "id": "postmarketos_wiki",
            "name": "postmarketOS Wiki",
            "url": f"https://wiki.postmarketos.org/wiki/Special:Search?search={search_term}",
        },
        {"id": "ubports_devices", "name": "Ubuntu Touch Devices", "url": "https://devices.ubuntu-touch.io/"},
    ]

    # --- IPFS index ---
    ipfs_roms = []
    index = ipfs_index_load()
    for _key, entry in index.items():
        if entry.get("codename") == codename:
            matched = False
            for r in results:
                if r["id"] == entry.get("rom_id") and r.get("filename") == entry.get("filename"):
                    r["ipfs_cid"] = entry["cid"]
                    matched = True
                    break
            if not matched:
                is_imported = entry.get("source") == "imported"
                ipfs_entry = {
                    "id": f"ipfs_{entry.get('rom_id', 'unknown')}",
                    "name": f"{entry.get('rom_name', 'ROM')} (IPFS)",
                    "version": entry.get("version", ""),
                    "filename": entry.get("filename", ""),
                    "download_url": "",
                    "page_url": "",
                    "ipfs_cid": entry["cid"],
                    "source": "community-ipfs" if is_imported else "ipfs",
                }
                # Replicant ROMs require Replicant's own recovery, not TWRP
                if entry.get("rom_id") == "replicant":
                    # Derive codename from filename (e.g. replicant-6.0-0004-transition-n7100.zip -> n7100)
                    fname = entry.get("filename", "")
                    rec_codename = fname.rsplit("-", 1)[-1].replace(".zip", "") if fname else codename
                    ipfs_entry["required_recovery"] = {
                        "id": "replicant-recovery",
                        "name": "Replicant Recovery",
                        "desc": "Replicant's own recovery — required to install Replicant ROMs.",
                        "type": "recovery",
                        "tags": ["recovery"],
                        "url": f"https://download.replicant.us/images/replicant-6.0/0004-transition/images/{rec_codename}/recovery-{rec_codename}.img",
                    }
                ipfs_roms.append(ipfs_entry)

    return jsonify(
        {
            "codename": codename,
            "model": model,
            "roms": results + ipfs_roms,
            "search_links": search_links,
        }
    )


@bp.route("/api/romfinder/download", methods=["POST"])
def api_romfinder_download():
    """Download a ROM file found by romfinder, optionally from IPFS."""
    url = request.json.get("url", "")
    filename = Path(request.json.get("filename", "rom.zip")).name
    if not filename or filename.startswith("."):
        filename = "rom.zip"
    codename = request.json.get("codename", "unknown")
    ipfs_cid = request.json.get("ipfs_cid", "")
    rom_id = request.json.get("rom_id", "")
    rom_name = request.json.get("rom_name", "")
    version = request.json.get("version", "")

    if not url and not ipfs_cid:
        return jsonify({"error": "No download URL or IPFS CID provided"}), 400

    target = Path.home() / "Osmosis-downloads" / codename
    dest = str(target / filename)

    def _run(task: Task):

        target.mkdir(parents=True, exist_ok=True)

        fetched_from_ipfs = False

        # Check IPFS index for a cached copy if no CID was provided
        effective_cid = ipfs_cid
        if not effective_cid and ipfs_available():
            cached = ipfs_index_lookup(codename, filename)
            if cached:
                effective_cid = cached["cid"]
                task.emit(f"Found in local IPFS cache: {effective_cid[:24]}...", "info")

        if effective_cid and ipfs_available():
            task.emit(f"Fetching from IPFS: {effective_cid}")
            task.emit(f"Destination: {dest}")
            task.emit("")
            rc = task.run_shell(["ipfs", "get", "-o", dest, effective_cid])
            if rc == 0:
                fetched_from_ipfs = True
            else:
                task.emit("IPFS fetch failed, falling back to HTTP download...", "warn")
                task.emit("")

        if not fetched_from_ipfs:
            if not url:
                task.emit("No HTTP download URL available.", "error")
                task.done(False)
                return
            task.emit(f"Downloading: {filename}")
            task.emit(f"URL: {url}", "cmd")
            task.emit(f"Destination: {dest}")
            task.emit("")
            # dl.twrp.me serves an HTML page first — the actual download
            # requires the referer to be the .html page on dl.twrp.me
            if "dl.twrp.me" in url:
                html_referer = url + ".html" if not url.endswith(".html") else url
                download_url = url.replace(".html", "") if url.endswith(".html") else url
                wget_cmd = [
                    "wget",
                    "--progress=dot:giga",
                    "-O",
                    dest,
                    f"--header=Referer: {html_referer}",
                    download_url,
                ]
            else:
                wget_cmd = ["wget", "--progress=dot:giga", "-O", dest, url]
            rc = task.run_shell(wget_cmd)

        if rc == 0:
            result = verify_fetched_file(dest)
            task.emit(f"SHA256: {result['sha256']}")
            if result["known"]:
                task.emit("Integrity check: file matches a known-good firmware entry.", "success")
            else:
                task.emit(
                    "Integrity warning: this file is NOT in the firmware registry. Verify before flashing.", "warn"
                )
            task.emit(f"Saved to: {dest}", "success")

            if not fetched_from_ipfs and ipfs_available():
                task.emit("")
                task.emit("Pinning to IPFS for future sharing...")
                cid = ipfs_pin_and_index(
                    dest,
                    key=f"{codename}/{filename}",
                    codename=codename,
                    rom_id=rom_id,
                    rom_name=rom_name,
                    version=version,
                )
                if cid:
                    task.emit(f"IPFS CID: {cid}", "success")
                    task.emit(f"Stored in IPFS index: {codename}/{filename}")
                else:
                    task.emit("IPFS pin failed (non-critical).", "warn")
        else:
            task.emit("Download failed.", "error")
            if Path(dest).exists():
                Path(dest).unlink(missing_ok=True)
        task.done(rc == 0)

    task_id = start_task(_run)
    return jsonify({"task_id": task_id, "dest": dest})


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
            "url": f"https://xdaforums.com/search/?q={search_term}+ROM&type=post",
            "desc": "Community forums for custom ROMs, mods, and troubleshooting",
        },
    ]

    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "6", f"https://xdaforums.com/search/?q={search_term}&type=post"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        forum_match = re.search(
            rf'href="(https://xdaforums\.com/[ct]/[^"]*{re.escape(codename)}[^"]*)"',
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
                "url": f"https://wiki.lineageos.org/devices/{codename}",
                "desc": "Official install guides and device info",
            },
            {
                "id": "pmos_wiki",
                "name": "postmarketOS Wiki",
                "icon": "wiki",
                "url": f"https://wiki.postmarketos.org/wiki/Special:Search?search={search_term}",
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
                "url": f"https://www.ifixit.com/Search?query={search_term}",
                "desc": "Repair guides and teardowns",
            },
            {
                "id": "gsmarena",
                "name": "GSMArena",
                "icon": "specs",
                "url": f"https://www.gsmarena.com/results.php3?sQuickSearch=yes&sName={search_term}",
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
                "url": f"https://www.sammobile.com/firmwares/?q={model}",
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
                ["curl", "-sL", "--max-time", "8", f"https://download.lineageos.org/api/v2/devices/{name}/builds"],
                capture_output=True,
                text=True,
                timeout=12,
            )
            builds = json.loads(r.stdout) if r.stdout.strip().startswith("[") else []
            if builds and isinstance(builds, list):
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
                        entry["download_url"] = f"https://mirrorbits.lineageos.org/full/{name}/{entry['filename']}"
                    if isinstance(entry["date"], (int, float)):
                        from datetime import datetime as dt

                        entry["date"] = dt.fromtimestamp(entry["date"]).strftime("%Y-%m-%d")
                    entries.append(entry)
                changelogs.append(
                    {
                        "rom_id": "lineageos",
                        "rom_name": "LineageOS",
                        "builds": entries,
                        "installed": installed_version,
                        "latest": entries[0]["version"] if entries else "",
                        "update_available": bool(
                            installed_version and entries and entries[0]["version"] != installed_version
                        ),
                    }
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
                ["curl", "-sL", "--max-time", "8", f"https://images.ecloud.global/stable/{name}/"],
                capture_output=True,
                text=True,
                timeout=12,
            )
            if r.returncode == 0 and "Not Found" not in r.stdout:
                eos_builds = re.findall(r'href="(e-[\d.]+-[^"]+\.zip)"', r.stdout)
                if eos_builds:
                    entries = []
                    for fname in reversed(eos_builds[-10:]):
                        m = re.search(r"e-([\d.]+)-", fname)
                        entries.append(
                            {
                                "version": m.group(1) if m else "",
                                "date": "",
                                "filename": fname,
                                "size": 0,
                                "download_url": f"https://images.ecloud.global/stable/{name}/{fname}",
                            }
                        )
                    entries.reverse()
                    changelogs.append(
                        {
                            "rom_id": "eos",
                            "rom_name": "/e/OS",
                            "builds": entries,
                            "installed": installed_version,
                            "latest": entries[0]["version"] if entries else "",
                            "update_available": bool(
                                installed_version and entries and entries[0]["version"] != installed_version
                            ),
                        }
                    )
                    break
        except Exception:
            pass

    return jsonify({"codename": codename, "changelogs": changelogs})
