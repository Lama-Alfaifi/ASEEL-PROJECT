from __future__ import annotations

import csv
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
LOCATION_FILE = BASE_DIR / "data" / "location_lookup.csv"


class LocationResolver:

    # Common names used by users that differ from the CSV names.
    CITY_ALIASES = {
        "riyadh": "riyadh city",
    }

    def __init__(self, csv_path: Path = LOCATION_FILE):
        self.csv_path = csv_path
        self.locations = []
        self.city_lookup = {}

        self._load()

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for reliable matching."""
        text = text.strip().lower()

        # Treat hyphens and underscores as spaces.
        text = re.sub(r"[-_]", " ", text)

        # Remove repeated spaces.
        text = re.sub(r"\s+", " ", text)

        return text

    def _load(self) -> None:
        """Load location lookup data from CSV."""

        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"Location lookup file not found: {self.csv_path}"
            )

        with self.csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:
                city = row.get("city", "").strip()

                if not city:
                    continue

                location = {
                    "city_id": row.get(
                        "city_id",
                        "",
                    ).strip(),

                    "planning_region": row.get(
                        "planning_region",
                        "",
                    ).strip(),

                    "administrative_region": row.get(
                        "administrative_region",
                        "",
                    ).strip(),

                    "governorate": row.get(
                        "governorate",
                        "",
                    ).strip(),

                    "city": city,
                }

                self.locations.append(location)

                normalized_city = self.normalize(city)

                self.city_lookup[normalized_city] = location

    def resolve(self, place: str) -> dict | None:
        """
        Resolve a city/place name to its geographic hierarchy.

        Example:
            Riyadh -> Riyadh City -> Central -> Riyadh
        """

        if not place:
            return None

        normalized_place = self.normalize(place)

        # Apply known aliases.
        normalized_place = self.CITY_ALIASES.get(
            normalized_place,
            normalized_place,
        )

        return self.city_lookup.get(normalized_place)

    def find_in_query(self, query: str) -> dict | None:
        """
        Find a known city/place mentioned in the user's query.
        """

        if not query:
            return None

        normalized_query = self.normalize(query)

        # ---------------------------------------------------------
        # 1. Check common aliases first.
        # ---------------------------------------------------------
        for alias, canonical_city in self.CITY_ALIASES.items():

            if alias in normalized_query:

                location = self.city_lookup.get(
                    canonical_city
                )

                if location:
                    return location

        # ---------------------------------------------------------
        # 2. Check exact city names from the CSV.
        # ---------------------------------------------------------
        for city_key, location in self.city_lookup.items():

            if city_key in normalized_query:
                return location

        return None


location_resolver = LocationResolver()

