from nyc_property_finder.services.duckdb_service import DuckDBService
from nyc_property_finder.services.schema import initialize_database


def test_initialize_database_creates_expected_property_explorer_gold_tables(tmp_path) -> None:
    database_path = tmp_path / "nyc_property_finder.duckdb"

    executed_files = initialize_database(database_path)

    assert executed_files
    with DuckDBService(database_path, read_only=True) as duckdb_service:
        tables = duckdb_service.query_df(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'property_explorer_gold'
            ORDER BY table_name
            """
        )["table_name"].tolist()

    assert tables == [
        "dim_property_listing",
        "dim_subway_stop",
        "dim_tract_to_nta",
        "dim_user_poi",
        "dim_user_poi_v2",
        "fct_nta_features",
        "fct_property_context",
        "fct_tract_features",
        "fct_user_shortlist",
    ]


def test_initialize_database_is_idempotent(tmp_path) -> None:
    database_path = tmp_path / "nyc_property_finder.duckdb"

    initialize_database(database_path)
    initialize_database(database_path)

    with DuckDBService(database_path, read_only=True) as duckdb_service:
        table_count = duckdb_service.query_df(
            """
            SELECT COUNT(*) AS table_count
            FROM information_schema.tables
            WHERE table_schema = 'property_explorer_gold'
            """
        )["table_count"].iloc[0]

    assert table_count == 9


def test_user_poi_v2_schema_is_source_aware(tmp_path) -> None:
    database_path = tmp_path / "nyc_property_finder.duckdb"

    initialize_database(database_path)

    with DuckDBService(database_path, read_only=True) as duckdb_service:
        columns = duckdb_service.query_df(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'property_explorer_gold'
              AND table_name = 'dim_user_poi_v2'
            ORDER BY ordinal_position
            """
        )["column_name"].tolist()

    assert columns == [
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


def test_property_context_schema_has_sprint_3_app_fields(tmp_path) -> None:
    database_path = tmp_path / "nyc_property_finder.duckdb"

    initialize_database(database_path)

    with DuckDBService(database_path, read_only=True) as duckdb_service:
        columns = duckdb_service.query_df(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'property_explorer_gold'
              AND table_name = 'fct_property_context'
            ORDER BY ordinal_position
            """
        )["column_name"].tolist()

    assert columns == [
        "property_id",
        "source",
        "source_listing_id",
        "address",
        "lat",
        "lon",
        "price",
        "beds",
        "baths",
        "listing_type",
        "active",
        "url",
        "ingest_timestamp",
        "tract_id",
        "nta_id",
        "nta_name",
        "nearest_subway_stop",
        "nearest_subway_distance_miles",
        "subway_lines_count",
        "poi_data_available",
        "poi_count_nearby",
        "poi_count_10min",
        "poi_category_counts",
        "neighborhood_score",
        "neighborhood_score_status",
        "mobility_score",
        "personal_fit_score",
        "personal_fit_score_status",
        "property_fit_score",
        "property_fit_score_status",
    ]
