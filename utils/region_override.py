"""
Explicit region selection coming from the UI region chips.

The UI sends one of: central / west / east / south / north / general,
or nothing at all when the chip is "Auto".

    None (Auto)  -> no override. Normal priority applies:
                    query location > conversation memory > detected location.
    a region     -> authoritative. Memory, remembered city and detected
                    location are ignored for this request.
    "General"    -> ALSO an explicit region choice (the nationwide KB records),
                    NOT "no region". It is handled exactly like the others.
"""
from __future__ import annotations

GENERAL = "General"

_CANONICAL = {
    "central": "Central",
    "west": "West",
    "western": "West",
    "east": "East",
    "eastern": "East",
    "south": "South",
    "southern": "South",
    "north": "North",
    "northern": "North",
    "general": GENERAL,
}


def normalize_region_override(value: str | None) -> str | None:
    """Return the canonical region label, or None for Auto / empty / unknown."""
    if value is None:
        return None

    key = str(value).strip().lower()

    if not key or key == "auto":
        return None

    return _CANONICAL.get(key)
