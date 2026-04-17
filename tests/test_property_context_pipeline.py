import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from nyc_property_finder.pipelines.build_property_context import run
from nyc_property_finder.services.duckdb_service import DuckDBService
from nyc_property_finder.services.schema import initialize_database


def test_run_builds_and_writes_property_context(tmp_path) -> None:
    database_path = tmp_path / "nyc_property_finder.duckdb"
    tract_path = tmp_path / "tracts.geojson"
    initialize_database(database_path)

    tracts = gpd.GeoDataFrame(
        [{"tract_id": "t1", "geometry": Polygon([(-74, 40.6), (-73.8, 40.6), (-73.8, 40.8), (-74, 40.8)])}],
        crs="EPSG:4326",
    )
    tracts.to_file(tract_path, driver="GeoJSON")

    with DuckDBService(database_path) as duckdb_service:
        duckdb_service.write_dataframe(
            pd.DataFrame(
                [
                    {
                        "property_id": "p1",
                        "source": "fixture",
                        "source_listing_id": "abc",
                        "address": "1 Main St",
                        "lat": 40.7,
                        "lon": -73.9,
                        "price": 3500,
                        "beds": 1,
                        "baths": 1,
                        "listing_type": "rental",
                        "url": "https://example.com/abc",
                        "ingest_timestamp": pd.Timestamp.now(tz="UTC"),
                    }
                ]
            ),
            table_name="dim_property_listing",
            schema="gold",
        )
        duckdb_service.write_dataframe(
            pd.DataFrame([{"tract_id": "t1", "nta_id": "n1", "nta_name": "Test NTA", "geometry_wkt": ""}]),
            table_name="dim_tract_to_nta",
            schema="gold",
        )
        duckdb_service.write_dataframe(
            pd.DataFrame(
                [
                    {
                        "subway_stop_id": "A01",
                        "stop_name": "Main St",
                        "lines": "A C",
                        "lat": 40.7005,
                        "lon": -73.9005,
                    }
                ]
            ),
            table_name="dim_subway_stop",
            schema="gold",
        )
        duckdb_service.write_dataframe(
            pd.DataFrame(
                [
                    {
                        "poi_id": "poi1",
                        "name": "Coffee Place",
                        "category": "coffee_shops",
                        "source_list_name": "Favorites",
                        "lat": 40.701,
                        "lon": -73.901,
                    }
                ]
            ),
            table_name="dim_user_poi",
            schema="gold",
        )
        duckdb_service.write_dataframe(
            pd.DataFrame(
                [
                    {
                        "tract_id": "t1",
                        "median_income": 100000,
                        "median_rent": 2500,
                        "median_home_value": 900000,
                        "pct_bachelors_plus": 0.6,
                        "median_age": 36,
                        "crime_rate_proxy": 1,
                    }
                ]
            ),
            table_name="fct_tract_features",
            schema="gold",
        )

    context = run(database_path=database_path, tract_path=tract_path)

    assert len(context) == 1
    assert context.iloc[0]["tract_id"] == "t1"
    assert context.iloc[0]["nta_id"] == "n1"
    assert context.iloc[0]["nearest_subway_stop"] == "Main St"
    assert context.iloc[0]["poi_count_10min"] == 1
    assert context.iloc[0]["property_fit_score"] > 0
    assert context.iloc[0]["poi_category_counts"] == '{"coffee_shops": 1}'

    with DuckDBService(database_path, read_only=True) as duckdb_service:
        persisted = duckdb_service.query_df("SELECT * FROM gold.fct_property_context")

    assert len(persisted) == 1
    assert persisted.iloc[0]["property_id"] == "p1"
