import pandas as pd
import pytest

from nyc_property_finder.pipelines.ingest_subway_stops import ingest_subway_stops, run
from nyc_property_finder.services.duckdb_service import DuckDBService
from nyc_property_finder.services.schema import initialize_database


def test_ingest_subway_stops_normalizes_alias_columns(tmp_path) -> None:
    stops_path = tmp_path / "subway_stops.csv"
    pd.DataFrame(
        [
            {"stop_id": "A01", "name": "Main St", "line": "A C", "lat": "40.7", "lon": "-73.9"},
            {"stop_id": "A01", "name": "Main St Updated", "line": "A C E", "lat": "40.7", "lon": "-73.9"},
        ]
    ).to_csv(stops_path, index=False)

    stops = ingest_subway_stops(stops_path)

    assert len(stops) == 1
    assert stops.iloc[0]["subway_stop_id"] == "A01"
    assert stops.iloc[0]["stop_name"] == "Main St Updated"
    assert stops.iloc[0]["lines"] == "A C E"


def test_ingest_subway_stops_requires_minimum_columns(tmp_path) -> None:
    stops_path = tmp_path / "subway_stops.csv"
    pd.DataFrame([{"stop_id": "A01", "lat": 40.7, "lon": -73.9}]).to_csv(stops_path, index=False)

    with pytest.raises(ValueError, match="Missing required subway stop columns"):
        ingest_subway_stops(stops_path)


def test_run_writes_subway_stops_to_duckdb(tmp_path) -> None:
    database_path = tmp_path / "nyc_property_finder.duckdb"
    stops_path = tmp_path / "subway_stops.csv"
    initialize_database(database_path)
    pd.DataFrame(
        [{"subway_stop_id": "A01", "stop_name": "Main St", "lines": "A C", "lat": 40.7, "lon": -73.9}]
    ).to_csv(stops_path, index=False)

    run(path=stops_path, database_path=database_path)

    with DuckDBService(database_path, read_only=True) as duckdb_service:
        stops = duckdb_service.query_df("SELECT * FROM gold.dim_subway_stop")

    assert len(stops) == 1
    assert stops.iloc[0]["stop_name"] == "Main St"
