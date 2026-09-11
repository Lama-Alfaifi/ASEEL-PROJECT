from __future__ import annotations
import re

REGION_ALIASES = {
    "West": ("west", "jeddah", "makkah", "mecca", "madinah", "medina"),
    "Central": ("central", "riyadh", "qassim", "al qassim"),
    "East": ("east", "dammam", "khobar", "dhahran", "al ahsa"),
    "South": ("south", "abha", "jazan", "najran", "al baha"),
    "North": ("north", "tabuk", "al jawf", "hail", "ha'il"),
    "General": ("general",),
}

def resolve_region(text: str) -> str | None:
    """Resolve an explicitly stated Saudi region or supported city alias."""
    for region, aliases in REGION_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE) for alias in aliases):
            return region
    return None
