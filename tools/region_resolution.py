from __future__ import annotations

import re


REGION_ALIASES = {
    "West": (
        "west",
        "western",
        "western region",
        "west region",
        "western saudi arabia",
        "west saudi arabia",
        "jeddah",
        "makkah",
        "mecca",
        "madinah",
        "medina",
        "hijaz",
        "hejazi",
        "taif",
    ),

    "Central": (
        "central",
        "central region",
        "central saudi arabia",
        "central area",
        "riyadh",
        "qassim",
        "al qassim",
        "najd",
    ),

    "East": (
        "east",
        "eastern",
        "eastern region",
        "east region",
        "eastern saudi arabia",
        "east saudi arabia",
        "dammam",
        "khobar",
        "dhahran",
        "al ahsa",
        "ahsaa",
    ),

    "South": (
        "south",
        "southern",
        "southern region",
        "south region",
        "southern saudi arabia",
        "southern area",
        "asir",
        "abha",
        "jazan",
        "najran",
        "al baha",
    ),

    "North": (
        "north",
        "northern",
        "northern region",
        "north region",
        "northern saudi arabia",
        "tabuk",
        "al jawf",
        "hail",
        "ha'il",
    ),

    "General": (
        "general",
    ),
}


def resolve_region(text: str) -> str | None:
    """Resolve a Saudi region or supported geographic alias into a canonical region."""

    if not text:
        return None

    for region, aliases in REGION_ALIASES.items():
        for alias in aliases:
            pattern = rf"\b{re.escape(alias)}\b"

            if re.search(pattern, text, re.IGNORECASE):
                return region

    return None




# from __future__ import annotations
# import re

# REGION_ALIASES = {
#     "West": ("west", "jeddah", "makkah", "mecca", "madinah", "medina"),
#     "Central": ("central", "riyadh", "qassim", "al qassim"),
#     "East": ("east", "dammam", "khobar", "dhahran", "al ahsa"),
#     "South": ("south", "abha", "jazan", "najran", "al baha"),
#     "North": ("north", "tabuk", "al jawf", "hail", "ha'il"),
#     "General": ("general",),
# }

# def resolve_region(text: str) -> str | None:
#     """Resolve an explicitly stated Saudi region or supported city alias."""
#     for region, aliases in REGION_ALIASES.items():
#         if any(re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE) for alias in aliases):
#             return region
#     return None
