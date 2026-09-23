from __future__ import annotations

import json
from pathlib import Path

from config.settings import ROOT_DIR
from retrieval.vector_store import CulturalVectorStore
from utils.location_resolver import location_resolver


GEOJSON_FILE = ROOT_DIR / "data" / "regions.geojson"

# regions.geojson (homaily/Saudi-Arabia-Regions-Cities-and-Districts) and
# data/location_lookup.csv each name Saudi Arabia's 13 official
# administrative regions independently. Their spelling agrees for 11 of
# them; these are the only two mismatches found by inspecting both files
# directly. This is a fixed correction for two known spelling differences
# between these two specific sources — not a general fuzzy-match rule.
GEOJSON_NAME_TO_ADMIN_REGION = {
    "Bahah": "Al Baha",
    "Jawf": "Al Jouf",
}


def _load_geojson() -> dict | None:
    if not GEOJSON_FILE.exists():
        return None

    try:
        with GEOJSON_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return None


def build_planning_region_map(geojson: dict) -> dict[str, str]:
    """
    Map each geojson feature's administrative region name (properties.name_en)
    to ASEEL's canonical planning region (East/West/North/South/Central),
    reusing location_lookup.csv (via location_resolver) as the single source
    of truth for that mapping — no separate, hardcoded region table.

    Values are normalized through CulturalVectorStore.normalize_region() so
    they match the canonical short form (e.g. "East") that ask() actually
    returns in result["region"] — location_lookup.csv itself stores the
    longer form ("Eastern"), and comparing those two forms directly is
    exactly the silent-mismatch bug this project has hit and fixed several
    times elsewhere in the pipeline (evidence_validation.py,
    cultural_search.py, agents/response.py).
    """

    admin_to_planning: dict[str, str] = {}

    for location in location_resolver.locations:
        admin = location.get("administrative_region")
        planning = CulturalVectorStore.normalize_region(
            location.get("planning_region")
        )

        if admin and planning and admin not in admin_to_planning:
            admin_to_planning[admin] = planning

    mapping: dict[str, str] = {}

    for feature in geojson.get("features", []):
        name_en = feature.get("properties", {}).get("name_en")

        if not name_en:
            continue

        admin_name = GEOJSON_NAME_TO_ADMIN_REGION.get(name_en, name_en)
        planning_region = admin_to_planning.get(admin_name)

        if planning_region:
            mapping[name_en] = planning_region

    return mapping


def load_regions() -> tuple[dict | None, dict[str, str]]:
    """
    Returns (geojson, {geojson_name_en: canonical_planning_region}).

    geojson is None if the file is missing or invalid — callers (the
    Streamlit UI) must handle that gracefully rather than crashing, per the
    project's error-handling requirements for the map feature.
    """

    geojson = _load_geojson()

    if geojson is None:
        return None, {}

    return geojson, build_planning_region_map(geojson)