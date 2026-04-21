import pandas as pd

from nyc_property_finder.app.neighborhood_qa import (
    build_metric_coverage,
    build_source_status,
    build_table_status,
)
from nyc_property_finder.services.duckdb_service import DuckDBService


def _write_gold_fixtures(database_path) -> None:
    mapping = pd.DataFrame(
        [
            {
                "tract_id": "36047000100",
                "nta_id": "BK0101",
                "nta_name": "Test Brooklyn",
                "borough": "Brooklyn",
            },
            {
                "tract_id": "36061000100",
                "nta_id": "MN0101",
                "nta_name": "Test Manhattan",
                "borough": "Manhattan",
            },
        ]
    )
    tract_features = pd.DataFrame(
        [
            {
                "tract_id": "36047000100",
                "median_income": 100000,
                "median_rent": 2500,
                "median_home_value": 900000,
                "pct_bachelors_plus": 0.5,
                "median_age": 35,
            },
            {
                "tract_id": "36061000100",
                "median_income": None,
                "median_rent": 3200,
                "median_home_value": 1200000,
                "pct_bachelors_plus": 0.7,
                "median_age": 42,
            },
        ]
    )
    nta_features = pd.DataFrame(
        [
            {
                "nta_id": "BK0101",
                "nta_name": "Test Brooklyn",
                "median_income": 100000,
                "median_rent": 2500,
                "median_home_value": 900000,
                "pct_bachelors_plus": 0.5,
                "median_age": 35,
            }
        ]
    )
    with DuckDBService(database_path) as duckdb_service:
        duckdb_service.write_dataframe(mapping, "dim_tract_to_nta", schema="property_explorer_gold")
        duckdb_service.write_dataframe(
            tract_features,
            "fct_tract_features",
            schema="property_explorer_gold",
        )
        duckdb_service.write_dataframe(
            nta_features,
            "fct_nta_features",
            schema="property_explorer_gold",
        )


def test_neighborhood_qa_summarizes_tables_and_metric_coverage(tmp_path) -> None:
    database_path = tmp_path / "app.duckdb"
    _write_gold_fixtures(database_path)

    table_status = build_table_status(database_path)
    tract_coverage = build_metric_coverage(database_path, "tract")

    assert table_status["Status"].tolist() == ["ready", "ready", "ready"]
    assert table_status.loc[table_status["Area"] == "Tract features", "Rows"].iloc[0] == 2

    median_income = tract_coverage[tract_coverage["Column"] == "median_income"].iloc[0]
    assert median_income["Rows"] == 2
    assert median_income["Populated"] == 1
    assert median_income["Coverage label"] == "50.0%"


def test_neighborhood_qa_reports_configured_source_path_status(tmp_path) -> None:
    ready_file = tmp_path / "ready.geojson"
    ready_file.write_text("{}", encoding="utf-8")
    data_sources = {
        "sources": {
            "ready_source": {
                "path": "ready.geojson",
                "expected_format": "geojson",
                "owner": "manual_download",
            },
            "missing_source": {
                "path": "missing.csv",
                "expected_format": "csv",
                "owner": "manual_download",
            },
        }
    }

    source_status = build_source_status(data_sources, project_root=tmp_path)

    assert source_status.loc[source_status["Source"] == "ready_source", "Status"].iloc[0] == "ready"
    assert (
        source_status.loc[source_status["Source"] == "missing_source", "Status"].iloc[0]
        == "missing"
    )
