import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from nyc_property_finder.app.base_map import (
    TARGET_COUNTY_GEOIDS,
    add_metric_display_columns,
    format_metric_value,
    prepare_base_map_data,
)
from nyc_property_finder.services.duckdb_service import DuckDBService


def _write_tract_fixture(path) -> None:
    tracts = gpd.GeoDataFrame(
        [
            {
                "GEOID": "36047000100",
                "BoroName": "Brooklyn",
                "NTA2020": "BK0101",
                "NTAName": "Test Brooklyn",
                "geometry": Polygon(
                    [(-74.00, 40.70), (-73.99, 40.70), (-73.99, 40.71), (-74.00, 40.71)]
                ),
            },
            {
                "GEOID": "36061000100",
                "BoroName": "Manhattan",
                "NTA2020": "MN0101",
                "NTAName": "Test Manhattan",
                "geometry": Polygon(
                    [(-73.99, 40.71), (-73.98, 40.71), (-73.98, 40.72), (-73.99, 40.72)]
                ),
            },
            {
                "GEOID": "36081000100",
                "BoroName": "Queens",
                "NTA2020": "QN0101",
                "NTAName": "Skipped Queens",
                "geometry": Polygon(
                    [(-73.98, 40.72), (-73.97, 40.72), (-73.97, 40.73), (-73.98, 40.73)]
                ),
            },
        ],
        geometry="geometry",
        crs="EPSG:4326",
    )
    tracts.to_file(path, driver="GeoJSON")


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
                "crime_rate_proxy": None,
            },
            {
                "tract_id": "36061000100",
                "median_income": 150000,
                "median_rent": 3200,
                "median_home_value": 1200000,
                "pct_bachelors_plus": 0.7,
                "median_age": 42,
                "crime_rate_proxy": None,
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
                "crime_rate_proxy": None,
            },
            {
                "nta_id": "MN0101",
                "nta_name": "Test Manhattan",
                "median_income": 150000,
                "median_rent": 3200,
                "median_home_value": 1200000,
                "pct_bachelors_plus": 0.7,
                "median_age": 42,
                "crime_rate_proxy": None,
            },
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


def test_format_metric_value_handles_currency_percent_and_nulls() -> None:
    assert format_metric_value(123456.7, "median_income") == "$123,457"
    assert format_metric_value(0.42, "pct_bachelors_plus") == "42.0%"
    assert format_metric_value(None, "median_age") == "Unavailable"


def test_add_metric_display_columns_marks_null_values_with_muted_color() -> None:
    data = gpd.GeoDataFrame(
        [{"median_income": 100}, {"median_income": None}],
        geometry=[
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
        ],
        crs="EPSG:4326",
    )

    output = add_metric_display_columns(data, "median_income")

    assert output["metric_available"].tolist() == [True, False]
    assert output.iloc[0]["fill_color"][3] > output.iloc[1]["fill_color"][3]


def test_prepare_base_map_data_filters_to_target_boroughs_and_joins_metrics(tmp_path) -> None:
    database_path = tmp_path / "app.duckdb"
    tract_path = tmp_path / "tracts.geojson"
    _write_tract_fixture(tract_path)
    _write_gold_fixtures(database_path)

    map_data = prepare_base_map_data(database_path, tract_path, metric="median_income")

    assert set(map_data.tracts["tract_id"]) == {"36047000100", "36061000100"}
    assert tuple(TARGET_COUNTY_GEOIDS) == ("36047", "36061")
    assert map_data.stats["tract_count"] == 2
    assert map_data.stats["neighborhood_count"] == 2
    assert map_data.stats["metric_non_null_count"] == 2
    assert map_data.tracts["median_income"].tolist() == [100000, 150000]
