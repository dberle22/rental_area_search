"""Ingest property listings from a local CSV or JSON file."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nyc_property_finder.services.duckdb_service import DuckDBService
from nyc_property_finder.transforms.listings import normalize_property_listings


REQUIRED_LISTING_COLUMNS = {"address", "lat", "lon", "price"}


def read_property_file(path: str | Path) -> pd.DataFrame:
    """Read a local property listing file from CSV or JSON."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Property listing file does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".json":
        return pd.read_json(path)
    raise ValueError(f"Unsupported property listing file format: {suffix}")


def validate_property_listings(dataframe: pd.DataFrame) -> None:
    """Validate the minimum source columns needed for MVP listing ingestion."""

    missing_columns = REQUIRED_LISTING_COLUMNS.difference(dataframe.columns)
    if missing_columns:
        raise ValueError(f"Missing required listing columns: {sorted(missing_columns)}")


def ingest_property_file(path: str | Path, source: str = "local_file") -> pd.DataFrame:
    """Read, validate, normalize, and deduplicate local listing records."""

    raw_listings = read_property_file(path)
    validate_property_listings(raw_listings)
    listings = normalize_property_listings(raw_listings, source=source)
    listings = listings.dropna(subset=["lat", "lon"])
    return listings.drop_duplicates("property_id", keep="last").reset_index(drop=True)


def write_property_listings(
    listings: pd.DataFrame,
    duckdb_service: DuckDBService,
    table_name: str = "dim_property_listing",
    schema: str = "gold",
) -> None:
    """Persist normalized property listings."""

    duckdb_service.write_dataframe(listings, table_name=table_name, schema=schema, if_exists="replace")


def run(path: str | Path, database_path: str | Path, source: str = "local_file") -> pd.DataFrame:
    """Pipeline entry point for local property listing ingestion."""

    listings = ingest_property_file(path=path, source=source)
    with DuckDBService(database_path) as duckdb_service:
        write_property_listings(listings, duckdb_service)
    return listings
