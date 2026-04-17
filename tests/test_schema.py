from nyc_property_finder.services.duckdb_service import DuckDBService
from nyc_property_finder.services.schema import initialize_database


def test_initialize_database_creates_expected_gold_tables(tmp_path) -> None:
    database_path = tmp_path / "nyc_property_finder.duckdb"

    executed_files = initialize_database(database_path)

    assert executed_files
    with DuckDBService(database_path, read_only=True) as duckdb_service:
        tables = duckdb_service.query_df(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'gold'
            ORDER BY table_name
            """
        )["table_name"].tolist()

    assert tables == [
        "dim_property_listing",
        "dim_subway_stop",
        "dim_tract_to_nta",
        "dim_user_poi",
        "fct_nta_features",
        "fct_property_context",
        "fct_tract_features",
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
            WHERE table_schema = 'gold'
            """
        )["table_count"].iloc[0]

    assert table_count == 7
