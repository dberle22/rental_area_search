"""Build the app-ready dim_user_poi_v2 dataframe."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

from nyc_property_finder.google_places_poi.cache import read_details_cache, read_resolution_cache
from nyc_property_finder.google_places_poi.config import DEFAULT_DETAILS_CACHE_PATH, DEFAULT_RESOLUTION_CACHE_PATH


DIM_USER_POI_V2_COLUMNS = [
    "poi_id",
    "source_system",
    "source_record_id",
    "source_list_names",
    "categories",
    "primary_category",
    "name",
    "input_title",
    "note",
    "tags",
    "comment",
    "source_url",
    "google_place_id",
    "match_status",
    "address",
    "lat",
    "lon",
    "details_fetched_at",
]


def build_dim_user_poi_v2(
    resolution_cache_path: str | Path = DEFAULT_RESOLUTION_CACHE_PATH,
    details_cache_path: str | Path = DEFAULT_DETAILS_CACHE_PATH,
) -> pd.DataFrame:
    """Build one deduplicated POI row per Google place ID."""

    resolution_cache = read_resolution_cache(resolution_cache_path)
    details_cache = read_details_cache(details_cache_path)
    resolved = resolution_cache[resolution_cache["google_place_id"] != ""].copy()
    if resolved.empty:
        return pd.DataFrame(columns=DIM_USER_POI_V2_COLUMNS)

    rows: list[dict[str, Any]] = []
    for google_place_id, group in resolved.groupby("google_place_id", sort=True):
        details_row = details_cache.get(google_place_id, {})
        payload = details_row.get("payload", {}) if isinstance(details_row, dict) else {}
        if not isinstance(payload, dict):
            payload = {}

        # Details payloads are the Google-standardized source for display name,
        # address, and map coordinates. Fall back to source title if needed.
        display_name = payload.get("displayName", {})
        name = display_name.get("text") if isinstance(display_name, dict) else None
        location = payload.get("location", {})
        first = group.iloc[0]

        rows.append(
            {
                "poi_id": _stable_poi_id("google_places", google_place_id),
                "source_system": "google_places",
                "source_record_id": _json_array(group["source_record_id"]),
                "source_list_names": _json_array(group["source_list_name"]),
                "categories": _json_array(group["category"].map(_fallback_category)),
                "primary_category": _fallback_category(first["category"]),
                "name": name or first["input_title"],
                "input_title": first["input_title"],
                "note": _json_array(group["note"]),
                "tags": _json_array(group["tags"]),
                "comment": _json_array(group["comment"]),
                "source_url": _json_array(group["source_url"]),
                "google_place_id": google_place_id,
                "match_status": first["match_status"],
                "address": payload.get("formattedAddress", ""),
                "lat": _location_value(location, "latitude"),
                "lon": _location_value(location, "longitude"),
                "details_fetched_at": details_row.get("fetched_at", ""),
            }
        )

    output = pd.DataFrame(rows)
    output["details_fetched_at"] = pd.to_datetime(output["details_fetched_at"], errors="coerce")
    output["lat"] = pd.to_numeric(output["lat"], errors="coerce")
    output["lon"] = pd.to_numeric(output["lon"], errors="coerce")
    return output[DIM_USER_POI_V2_COLUMNS]


def _stable_poi_id(source_system: str, stable_source_key: str) -> str:
    key = f"{source_system.strip().lower()}|{stable_source_key.strip()}"
    return f"poi_{sha256(key.encode('utf-8')).hexdigest()[:16]}"


def _json_array(values: pd.Series) -> str:
    # Store multi-list fields as JSON text for now. This keeps dim_user_poi_v2
    # one-row-per-place while preserving source membership for later modeling.
    cleaned = []
    for value in values.fillna("").astype(str):
        value = value.strip()
        if value and value not in cleaned:
            cleaned.append(value)
    return json.dumps(cleaned, ensure_ascii=False)


def _fallback_category(category: str) -> str:
    return str(category).strip() or "other"


def _location_value(location: Any, key: str) -> float | None:
    if not isinstance(location, dict):
        return None
    value = location.get(key)
    return float(value) if value not in (None, "") else None
