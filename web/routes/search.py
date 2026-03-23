"""Unified search route — searches across all device types."""

from flask import Blueprint, jsonify, request

from web.core import parse_devices_cfg, parse_microcontrollers_cfg

bp = Blueprint("search", __name__)


def _score(haystack: str, query: str) -> int:
    """Score a match: higher is better. 0 means no match."""
    h = haystack.lower()
    q = query.lower()
    if q == h:
        return 10
    if h.startswith(q):
        return 8
    if q in h:
        return 5
    # Check each query word
    words = q.split()
    if all(w in h for w in words):
        return 3
    if any(w in h for w in words):
        return 1
    return 0


# Brand aliases — map common brand names to patterns found in device labels
_BRAND_ALIASES: dict[str, list[str]] = {
    "samsung": ["galaxy", "sm-"],
    "google": ["pixel"],
    "xiaomi": ["poco", "redmi", "mi "],
    "raspberry": ["raspberry pi", "rpi"],
    "arduino": ["arduino"],
    "ninebot": ["ninebot", "nb-"],
    "segway": ["ninebot", "segway"],
    "apple": ["macbook", "imac", "mac mini", "mac pro"],
}


_MODEL_PREFIX_BRANDS = {
    "SM-": "Samsung",
    "Pixel": "Google",
    "IN20": "OnePlus",
    "KB20": "OnePlus",
    "M20": "Xiaomi",
    "220": "Xiaomi",
    "FP": "Fairphone",
    "moto": "Motorola",
    "XT": "Motorola",
    "XQ-": "Sony",
    "A06": "Nothing",
    "Pine": "Pine64",
    "Librem": "Purism",
}


def _infer_phone_brand(dev: dict) -> str:
    """Infer brand from model number or label."""
    model = dev.get("model", "")
    label = dev.get("label", "")
    for prefix, brand in _MODEL_PREFIX_BRANDS.items():
        if model.startswith(prefix) or label.startswith(prefix):
            return brand
    # Common label patterns
    if "Galaxy" in label:
        return "Samsung"
    if "Pixel" in label:
        return "Google"
    if "OnePlus" in label:
        return "OnePlus"
    if "Redmi" in label or "POCO" in label:
        return "Xiaomi"
    if "Xperia" in label:
        return "Sony"
    if "Fairphone" in label:
        return "Fairphone"
    if "Nothing" in label:
        return "Nothing"
    if "PinePhone" in label or "PineTab" in label:
        return "Pine64"
    if "Librem" in label:
        return "Purism"
    if "Moto" in label:
        return "Motorola"
    return ""


@bp.route("/api/search")
def api_search():
    """Search across all device types.

    Query params: ?q=<query>
    Returns a unified list of results with type, id, label, and metadata.
    """
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])

    # Expand brand aliases: "samsu" / "samsung" -> also search "galaxy", "sm-"
    queries = [q]
    ql = q.lower()
    for brand, aliases in _BRAND_ALIASES.items():
        if ql.startswith(brand) or brand.startswith(ql):
            queries.extend(aliases)

    results = []

    # --- Phones / tablets ---
    for dev in parse_devices_cfg():
        haystack = f"{dev.get('label', '')} {dev.get('model', '')} {dev.get('codename', '')} {dev.get('id', '')}"
        s = max(_score(haystack, query) for query in queries)
        if s > 0:
            # Infer brand from model prefix or label
            brand = _infer_phone_brand(dev)
            results.append(
                {
                    "type": "phone",
                    "id": dev["id"],
                    "label": dev.get("label", ""),
                    "brand": brand,
                    "subtitle": dev.get("model", ""),
                    "codename": dev.get("codename", ""),
                    "has_rom": bool(dev.get("rom_url")),
                    "has_eos": bool(dev.get("eos_url")),
                    "has_twrp": bool(dev.get("twrp_url")),
                    "_score": s,
                }
            )

    # --- Microcontrollers ---
    for board in parse_microcontrollers_cfg():
        haystack = f"{board.get('label', '')} {board.get('brand', '')} {board.get('arch', '')} {board.get('id', '')}"
        s = max(_score(haystack, query) for query in queries)
        if s > 0:
            results.append(
                {
                    "type": "microcontroller",
                    "id": board["id"],
                    "label": board.get("label", ""),
                    "brand": board.get("brand", ""),
                    "subtitle": f"{board.get('brand', '')} \u00b7 {board.get('arch', '')}",
                    "_score": s,
                }
            )

    # --- Scooters ---
    try:
        from web.routes.scooter import parse_scooters_cfg

        for sc in parse_scooters_cfg():
            haystack = f"{sc.get('label', '')} {sc.get('brand', '')} {sc.get('id', '')}"
            s = _score(haystack, q)
            if s > 0:
                results.append(
                    {
                        "type": "scooter",
                        "id": sc["id"],
                        "label": sc.get("label", ""),
                        "brand": sc.get("brand", ""),
                        "subtitle": sc.get("brand", ""),
                        "_score": s,
                    }
                )
    except Exception:
        pass

    # --- E-bikes ---
    try:
        from web.routes.ebike import parse_ebikes_cfg

        for eb in parse_ebikes_cfg():
            haystack = f"{eb.get('label', '')} {eb.get('brand', '')} {eb.get('controller', '')} {eb.get('id', '')}"
            s = _score(haystack, q)
            if s > 0:
                results.append(
                    {
                        "type": "ebike",
                        "id": eb["id"],
                        "label": eb.get("label", ""),
                        "brand": eb.get("brand", ""),
                        "subtitle": eb.get("brand", ""),
                        "_score": s,
                    }
                )
    except Exception:
        pass

    # --- T2 Macs ---
    try:
        from web.routes.t2 import parse_t2_cfg

        for mac in parse_t2_cfg():
            haystack = f"{mac.get('label', '')} {mac.get('model', '')} {mac.get('id', '')}"
            s = _score(haystack, q)
            if s > 0:
                results.append(
                    {
                        "type": "t2",
                        "id": mac["id"],
                        "label": mac.get("label", ""),
                        "brand": "Apple",
                        "subtitle": mac.get("model", ""),
                        "_score": s,
                    }
                )
    except Exception:
        pass

    # Sort by score descending, limit to 20
    results.sort(key=lambda r: r["_score"], reverse=True)
    for r in results:
        r.pop("_score", None)

    return jsonify(results[:20])
