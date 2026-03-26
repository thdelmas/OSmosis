"""Flow definition loader.

Scans web/flows/*.yaml for declarative flow definitions and indexes
them by ID and by (category, brand) for quick lookup.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_FLOWS_DIR = Path(__file__).parent / "flows"
_cache: dict[str, dict] = {}


def load_flows(force: bool = False) -> dict[str, dict]:
    """Load all flow definitions from YAML files.

    Returns a dict keyed by flow ID.
    """
    global _cache
    if _cache and not force:
        return _cache

    _cache = {}
    if not _FLOWS_DIR.exists():
        return _cache

    for path in sorted(_FLOWS_DIR.glob("*.yaml")):
        try:
            with open(path) as f:
                flow = yaml.safe_load(f)
            if flow and "id" in flow:
                _cache[flow["id"]] = flow
        except Exception as e:
            print(f"Warning: failed to load flow {path.name}: {e}")

    return _cache


def get_flow(flow_id: str) -> dict | None:
    """Get a flow definition by ID."""
    flows = load_flows()
    return flows.get(flow_id)


def find_flows(
    category: str = "",
    brand: str = "",
    mode: str = "",
) -> list[dict]:
    """Find flows matching the given criteria."""
    flows = load_flows()
    results = []

    for flow in flows.values():
        # Category filter
        if category and flow.get("category", "") != category:
            continue

        # Brand filter
        if brand:
            brands = flow.get("brands", [])
            match_data = flow.get("match", {})
            match_brands = match_data.get("brand", [])
            all_brands = set(b.lower() for b in brands + match_brands)
            if brand.lower() not in all_brands:
                continue

        # Mode filter
        if mode:
            match_data = flow.get("match", {})
            match_modes = match_data.get("modes", [])
            if match_modes and mode not in match_modes:
                continue

        results.append(
            {
                "id": flow["id"],
                "name": flow.get("name", flow["id"]),
                "description": flow.get("description", ""),
                "category": flow.get("category", ""),
                "brands": flow.get("brands", []),
            }
        )

    return results
