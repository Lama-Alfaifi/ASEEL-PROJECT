"""
Turns a browser location into ASEEL's canonical city / planning region.

Reuses the existing sources of truth instead of adding a parallel mapping:
  * region  -> data/regions.geojson polygons (point-in-polygon) mapped to a
               planning region by utils.region_geography.load_regions(),
               i.e. the same admin-region -> planning-region logic the map uses.
  * city    -> nearest known city, validated through location_resolver so the
               name is exactly the one location_lookup.csv uses.

Coordinates are used only inside this module for the duration of a call.
Nothing here stores or logs them, and normalize_user_location() strips them
before anything enters the workflow state (which monitoring may record).
"""
from __future__ import annotations

import math
from functools import lru_cache

from retrieval.vector_store import CulturalVectorStore
from utils.location_resolver import location_resolver
from utils.region_geography import load_regions


_CANONICAL = {r.lower(): r for r in ("Central", "West", "East", "South", "North")}

REGION_PHRASE = {
    "Central": "Central Saudi Arabia",
    "West": "Western Saudi Arabia",
    "East": "Eastern Saudi Arabia",
    "South": "Southern Saudi Arabia",
    "North": "Northern Saudi Arabia",
}

# A point closer than this to a known city is labelled with that city.
CITY_RADIUS_KM = 45.0
# If the polygons give no region at all (coastline, simplified borders), a city
# this close is still trusted for the region.
REGION_FALLBACK_KM = 80.0

# (candidate names as they might appear in location_lookup.csv, lat, lon).
# Each anchor is validated through location_resolver at load time; names the
# CSV does not contain are skipped silently, and the first candidate that
# resolves is used. Approximate city-centre coordinates.
_CITY_ANCHORS: list[tuple[tuple[str, ...], float, float]] = [
    (("Riyadh",), 24.7136, 46.6753),
    (("Jeddah", "Jedda"), 21.4858, 39.1925),
    (("Makkah", "Mecca", "Makkah Al Mukarramah"), 21.3891, 39.8579),
    (("Madinah", "Medina", "Al Madinah"), 24.5247, 39.5692),
    (("Taif", "At Taif"), 21.2703, 40.4158),
    (("Rabigh",), 22.7986, 39.0349),
    (("Yanbu",), 24.0895, 38.0618),
    (("Dammam", "Ad Dammam"), 26.4207, 50.0888),
    (("Khobar", "Al Khobar"), 26.2172, 50.1971),
    (("Dhahran",), 26.2361, 50.0393),
    (("Hofuf", "Al Hofuf", "Al Ahsa"), 25.3648, 49.5876),
    (("Jubail", "Al Jubail"), 27.0046, 49.6460),
    (("Buraidah", "Buraydah"), 26.3260, 43.9750),
    (("Unaizah", "Unayzah"), 26.0840, 43.9940),
    (("Al Kharj", "Kharj"), 24.1556, 47.3120),
    (("Hail", "Ha'il"), 27.5114, 41.7208),
    (("Tabuk",), 28.3838, 36.5550),
    (("Sakaka",), 29.9697, 40.2064),
    (("Arar",), 30.9753, 41.0381),
    (("Abha",), 18.2164, 42.5053),
    (("Khamis Mushait",), 18.3000, 42.7300),
    (("Jazan", "Jizan"), 16.8892, 42.5511),
    (("Najran",), 17.4917, 44.1322),
    (("Al Baha", "Baha"), 20.0129, 41.4677),
    (("Al Qunfudhah", "Qunfudhah"), 19.1264, 41.0789),
]


def canonical_region(value: str | None) -> str | None:
    """Any spelling of a region -> Central/West/East/South/North, else None.
    "General" and unknown values deliberately return None."""
    if not value:
        return None
    normalized = CulturalVectorStore.normalize_region(value)
    if not normalized:
        return None
    return _CANONICAL.get(str(normalized).strip().lower())


# ---------------- geometry ----------------

def _ring_contains(ring: list, lon: float, lat: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _polygon_contains(polygon: list, lon: float, lat: float) -> bool:
    if not polygon or not _ring_contains(polygon[0], lon, lat):
        return False
    return not any(_ring_contains(hole, lon, lat) for hole in polygon[1:])


def _geometry_contains(geometry: dict, lon: float, lat: float) -> bool:
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        return _polygon_contains(coords, lon, lat)
    if kind == "MultiPolygon":
        return any(_polygon_contains(p, lon, lat) for p in coords)
    return False


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


# ---------------- lookups ----------------

@lru_cache(maxsize=1)
def _regions() -> tuple[dict | None, dict[str, str]]:
    return load_regions()


@lru_cache(maxsize=1)
def _anchors() -> list[tuple[dict, float, float]]:
    resolved: list[tuple[dict, float, float]] = []
    seen: set[str] = set()
    for names, lat, lon in _CITY_ANCHORS:
        for name in names:
            location = location_resolver.resolve(name)
            if location:
                if location["city"] not in seen:
                    seen.add(location["city"])
                    resolved.append((location, lat, lon))
                break
    return resolved


def _region_from_polygons(lat: float, lon: float) -> str | None:
    geojson, mapping = _regions()
    if not geojson:
        return None
    for feature in geojson.get("features", []):
        name = feature.get("properties", {}).get("name_en")
        if name in mapping and _geometry_contains(feature.get("geometry") or {}, lon, lat):
            return mapping[name]
    return None


def resolve_coordinates(latitude: float, longitude: float) -> dict:
    """{"city": str | None, "region": str | None}. Both None outside Saudi Arabia."""
    region = canonical_region(_region_from_polygons(latitude, longitude))

    nearest, distance = None, math.inf
    for location, lat, lon in _anchors():
        d = _haversine_km(latitude, longitude, lat, lon)
        if d < distance:
            nearest, distance = location, d

    city = None
    if nearest is not None:
        city_region = canonical_region(nearest.get("planning_region"))
        if distance <= CITY_RADIUS_KM and (region is None or city_region == region):
            city = nearest["city"]
            region = region or city_region
        elif region is None and distance <= REGION_FALLBACK_KM:
            region = city_region

    return {"city": city, "region": region}


# ---------------- workflow-facing helpers ----------------

def normalize_user_location(raw: dict | None) -> dict | None:
    """
    Validate an incoming location object and reduce it to {"city", "region"}.

    * city is accepted only if location_resolver knows it (its region then comes
      from location_lookup.csv, the single source of truth);
    * otherwise the supplied region is accepted if it is canonical;
    * otherwise, if raw coordinates were sent, they are resolved and discarded.

    Returns None when nothing usable remains. Coordinates never leave this function.
    """
    if not raw:
        return None

    city_name = (raw.get("city") or "").strip() or None
    location = location_resolver.resolve(city_name) if city_name else None

    city = location["city"] if location else None
    region = (
        canonical_region(location.get("planning_region"))
        if location
        else canonical_region(raw.get("region"))
    )

    lat, lon = raw.get("latitude"), raw.get("longitude")
    if region is None and lat is not None and lon is not None:
        resolved = resolve_coordinates(float(lat), float(lon))
        city = city or resolved["city"]
        region = resolved["region"]

    if not city and not region:
        return None
    return {"city": city, "region": region}


def describe_location(location: dict) -> str:
    """{"city": "Riyadh City", "region": "Central"} -> "Riyadh City, Central Saudi Arabia"."""
    parts = []
    if location.get("city"):
        parts.append(location["city"])
    phrase = REGION_PHRASE.get(location.get("region") or "")
    if phrase:
        parts.append(phrase)
    return ", ".join(parts)
