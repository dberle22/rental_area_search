"""Ingest subway stops from a local CSV or JSON file."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nyc_property_finder.services.duckdb_service import DuckDBService


SUBWAY_STOP_COLUMNS = ["subway_stop_id", "stop_name", "lines", "lat", "lon"]
REQUIRED_SUBWAY_STOP_COLUMNS = {"subway_stop_id", "stop_name", "lat", "lon"}
COLUMN_ALIASES = {
    "stop_id": "subway_stop_id",
    "id": "subway_stop_id",
    "name": "stop_name",
    "station_name": "stop_name",
    "line": "lines",
}


def read_subway_stops_file(path: str | Path) -> pd.DataFrame:
    """Read subway stop records from CSV or JSON."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Subway stops file does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".json":
        return pd.read_json(path)
    raise ValueError(f"Unsupported subway stops file format: {suffix}")


def normalize_subway_stops(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize subway stop records to the MVP schema."""

    output = dataframe.rename(
        columns={column: COLUMN_ALIASES[column] for column in dataframe.columns if column in COLUMN_ALIASES}
    ).copy()
    missing_columns = REQUIRED_SUBWAY_STOP_COLUMNS.difference(output.columns)
    if missing_columns:
        raise ValueError(f"Missing required subway stop columns: {sorted(missing_columns)}")

    if "lines" not in output.columns:
        output["lines"] = ""

    output["subway_stop_id"] = output["subway_stop_id"].fillna("").astype(str).str.strip()
    output["stop_name"] = output["stop_name"].fillna("").astype(str).str.strip()
    output["lines"] = output["lines"].fillna("").astype(str).str.strip()
    output["lat"] = pd.to_numeric(output["lat"], errors="coerce")
    output["lon"] = pd.to_numeric(output["lon"], errors="coerce")
    output = output.dropna(subset=["lat", "lon"])
    output = output[output["subway_stop_id"] != ""]
    return output[SUBWAY_STOP_COLUMNS].drop_duplicates("subway_stop_id", keep="last").reset_index(drop=True)


def ingest_subway_stops(path: str | Path) -> pd.DataFrame:
    """Read and normalize local subway stop records."""

    return normalize_subway_stops(read_subway_stops_file(path))


def write_subway_stops(
    stops: pd.DataFrame,
    duckdb_service: DuckDBService,
    table_name: str = "dim_subway_stop",
    schema: str = "gold",
) -> None:
    """Persist subway stops."""

    duckdb_service.write_dataframe(stops, table_name=table_name, schema=schema, if_exists="replace")


def run(path: str | Path, database_path: str | Path) -> pd.DataFrame:
    """Pipeline entry point for subway stop ingestion."""

    stops = ingest_subway_stops(path)
    with DuckDBService(database_path) as duckdb_service:
        write_subway_stops(stops, duckdb_service)
    return stops
