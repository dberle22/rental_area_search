"""POI parsing and normalization helpers."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from hashlib import sha256
from pathlib import Path

import pandas as pd


DEFAULT_CATEGORY_KEYWORDS = {
    "restaurants": ["restaurant", "diner", "pizza", "food"],
    "bars": ["bar", "brewery", "pub", "cocktail"],
    "parks": ["park", "garden", "playground"],
    "coffee_shops": ["coffee", "cafe", "espresso"],
    "groceries": ["grocery", "market", "supermarket"],
    "museums": ["museum", "gallery"],
    "shopping": ["shop", "store", "mall"],
}


def normalize_category(name: str, category_keywords: dict[str, list[str]] | None = None) -> str:
    """Map a place name into a coarse category."""

    category_keywords = category_keywords or DEFAULT_CATEGORY_KEYWORDS
    clean_name = name.lower()
    for category, keywords in category_keywords.items():
        if any(keyword in clean_name for keyword in keywords):
            return category
    return "other"


def parse_google_maps_json(path: str | Path) -> pd.DataFrame:
    """Parse a minimal Google Maps JSON export.

    Google exports vary by product/version, so this accepts either a list of
    places or a mapping with a ``places`` key.
    """

    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    places = data.get("places", data) if isinstance(data, dict) else data
    rows: list[dict[str, object]] = []
    for place in places:
        location = place.get("location", {})
        lat = place.get("lat", location.get("lat"))
        lon = place.get("lon", place.get("lng", location.get("lng")))
        rows.append(
            {
                "name": place.get("name", ""),
                "source_list_name": place.get("list_name", place.get("source_list_name", "google_maps")),
                "lat": lat,
                "lon": lon,
            }
        )
    return pd.DataFrame(rows)


def parse_google_maps_kml(path: str | Path) -> pd.DataFrame:
    """Parse placemarks from a KML file."""

    tree = ET.parse(path)
    root = tree.getroot()
    namespace_match = re.match(r"\{.*\}", root.tag)
    namespace = namespace_match.group(0) if namespace_match else ""
    rows: list[dict[str, object]] = []

    for placemark in root.iter(f"{namespace}Placemark"):
        name_node = placemark.find(f"{namespace}name")
        coordinates_node = placemark.find(f".//{namespace}coordinates")
        if coordinates_node is None or not coordinates_node.text:
            continue
        lon, lat, *_ = coordinates_node.text.strip().split(",")
        rows.append(
            {
                "name": name_node.text if name_node is not None else "",
                "source_list_name": "google_maps",
                "lat": float(lat),
                "lon": float(lon),
            }
        )

    return pd.DataFrame(rows)


def normalize_poi_dataframe(
    dataframe: pd.DataFrame,
    category_keywords: dict[str, list[str]] | None = None,
) -> pd.DataFrame:
    """Clean and categorize POI records."""

    output = dataframe.copy()
    output["name"] = output["name"].fillna("").astype(str).str.strip()
    output["lat"] = pd.to_numeric(output["lat"], errors="coerce")
    output["lon"] = pd.to_numeric(output["lon"], errors="coerce")
    output = output.dropna(subset=["lat", "lon"])
    output["category"] = output["name"].apply(lambda value: normalize_category(value, category_keywords))
    output["poi_id"] = output.apply(
        lambda row: _stable_poi_id(row["name"], row["lat"], row["lon"]),
        axis=1,
    )
    return output[["poi_id", "name", "category", "source_list_name", "lat", "lon"]]


def _stable_poi_id(name: str, lat: float, lon: float) -> str:
    """Generate a deterministic POI id."""

    key = f"{name.strip().lower()}|{round(lat, 6)}|{round(lon, 6)}"
    return f"poi_{sha256(key.encode('utf-8')).hexdigest()[:16]}"
