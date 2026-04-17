"""Ingest Google Maps saved places exports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nyc_property_finder.services.config import load_config
from nyc_property_finder.services.duckdb_service import DuckDBService
from nyc_property_finder.transforms.poi import (
    normalize_poi_dataframe,
    parse_google_maps_json,
    parse_google_maps_kml,
)


def parse_google_maps_export(path: str | Path) -> pd.DataFrame:
    """Parse a Google Maps export from KML or JSON."""

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        return parse_google_maps_json(path)
    if suffix == ".kml":
        return parse_google_maps_kml(path)
    raise ValueError(f"Unsupported Google Maps export format: {suffix}")


def ingest_google_maps(path: str | Path, category_keywords: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Parse and normalize a Google Maps export."""

    raw_poi = parse_google_maps_export(path)
    return normalize_poi_dataframe(raw_poi, category_keywords=category_keywords)


def write_poi(
    poi: pd.DataFrame,
    duckdb_service: DuckDBService,
    table_name: str = "dim_user_poi",
    schema: str = "gold",
) -> None:
    """Persist normalized POI records."""

    duckdb_service.write_dataframe(poi, table_name=table_name, schema=schema, if_exists="replace")


def run(
    path: str | Path,
    database_path: str | Path,
    category_keywords: dict[str, list[str]] | None = None,
) -> pd.DataFrame:
    """Pipeline entry point for Google Maps POI ingestion."""

    if category_keywords is None:
        category_keywords = load_config()["poi_categories"].get("categories")
    poi = ingest_google_maps(path, category_keywords=category_keywords)
    with DuckDBService(database_path) as duckdb_service:
        write_poi(poi, duckdb_service)
    return poi
