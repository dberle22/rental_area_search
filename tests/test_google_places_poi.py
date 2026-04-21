import json
import pytest

from nyc_property_finder.google_places_poi.build_dim import build_dim_user_poi_v2
from nyc_property_finder.google_places_poi.cache import read_details_cache, read_resolution_cache
from nyc_property_finder.google_places_poi.client import (
    PLACE_DETAILS_FIELD_MASK,
    TEXT_SEARCH_ID_FIELD_MASK,
    build_place_details_request,
    build_text_search_id_request,
)
from nyc_property_finder.google_places_poi.config import (
    get_google_maps_api_key,
    read_api_keys_file,
    read_env_file,
)
from nyc_property_finder.google_places_poi.dry_run import plan_dry_run, read_details_cache_place_ids
from nyc_property_finder.google_places_poi.enrich import enrich_place_details
from nyc_property_finder.google_places_poi.parse_takeout import (
    build_search_query,
    clean_list_category,
    parse_google_places_saved_list_csv,
)
from nyc_property_finder.google_places_poi.pipeline import run as run_google_places_poi
from nyc_property_finder.google_places_poi.resolve import resolve_place_ids
from nyc_property_finder.services.duckdb_service import DuckDBService


def test_parse_google_places_saved_list_csv_preserves_takeout_metadata(tmp_path) -> None:
    export_path = tmp_path / "New York - Bookstores.csv"
    export_path.write_text(
        "\n".join(
            [
                "Title,Note,URL,Tags,Comment",
                ",,,,",
                "Ursula Bookshop,near the park,https://www.google.com/maps/place/Ursula+Bookshop,books,check hours",
            ]
        ),
        encoding="utf-8",
    )

    parsed = parse_google_places_saved_list_csv(export_path)

    assert len(parsed) == 1
    row = parsed.iloc[0]
    assert row["source_record_id"].startswith("src_")
    assert row["source_system"] == "google_maps_takeout"
    assert row["source_file"] == "New York - Bookstores.csv"
    assert row["source_list_name"] == "New York - Bookstores"
    assert row["category"] == "bookstores"
    assert row["input_title"] == "Ursula Bookshop"
    assert row["note"] == "near the park"
    assert row["tags"] == "books"
    assert row["comment"] == "check hours"
    assert row["source_url"] == "https://www.google.com/maps/place/Ursula+Bookshop"
    assert row["search_query"] == "Ursula Bookshop New York, NY"


def test_parse_google_places_saved_list_csv_accepts_one_line_offset_header(tmp_path) -> None:
    export_path = tmp_path / "Restaurants.csv"
    export_path.write_text(
        "\n".join(
            [
                "Saved places",
                "Title,Note,URL,Tags,Comment",
                "Donovan's Pub,,https://www.google.com/maps/place/Donovan%27s+Pub,,",
            ]
        ),
        encoding="utf-8",
    )

    parsed = parse_google_places_saved_list_csv(export_path)

    assert parsed.iloc[0]["input_title"] == "Donovan's Pub"
    assert parsed.iloc[0]["category"] == "restaurants"
    assert parsed.iloc[0]["source_url"] == "https://www.google.com/maps/place/Donovan's+Pub"


def test_build_search_query_uses_simple_nyc_context() -> None:
    assert build_search_query("  Donovan's   Pub  ") == "Donovan's Pub New York, NY"
    assert build_search_query("Donovan's Pub", search_context="") == "Donovan's Pub"


def test_clean_list_category_uses_list_name() -> None:
    assert clean_list_category("New York - Cocktail Bars") == "cocktail_bars"
    assert clean_list_category("NYC Museums") == "museums"
    assert clean_list_category("") == "other"


def test_read_env_file_and_google_maps_api_key_fallback(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "NYC_PROPERTY_FINDER_ENV=local",
                "GOOGLE_MAPS_API_KEY='from-file'",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    assert read_env_file(env_path)["GOOGLE_MAPS_API_KEY"] == "from-file"
    assert get_google_maps_api_key(env_path=env_path) == "from-file"

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "from-env")
    assert get_google_maps_api_key(env_path=env_path) == "from-env"


def test_read_api_keys_file_supports_scalar_and_mapping(tmp_path, monkeypatch) -> None:
    api_keys_path = tmp_path / "api_keys.yaml"

    api_keys_path.write_text("from-scalar", encoding="utf-8")
    assert read_api_keys_file(api_keys_path) == "from-scalar"

    api_keys_path.write_text("google_maps_api_key: from-mapping", encoding="utf-8")
    assert read_api_keys_file(api_keys_path) == "from-mapping"

    api_keys_path.write_text("keys:\n  places_api_key: from-nested", encoding="utf-8")
    assert read_api_keys_file(api_keys_path) == "from-nested"

    api_keys_path.write_text("keys:\n  places_api_key:\n    key: from-wrapper", encoding="utf-8")
    assert read_api_keys_file(api_keys_path) == "from-wrapper"

    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    assert (
        get_google_maps_api_key(
            env_path=tmp_path / "missing.env",
            api_keys_path=api_keys_path,
        )
        == "from-wrapper"
    )


def test_plan_dry_run_estimates_calls_without_cache(tmp_path) -> None:
    export_path = tmp_path / "Restaurants.csv"
    export_path.write_text(
        "\n".join(
            [
                "Title,Note,URL,Tags,Comment",
                "Donovan's Pub,,https://www.google.com/maps/place/Donovan%27s+Pub,,",
                "Rolo's,,https://www.google.com/maps/place/Rolo%27s,,",
            ]
        ),
        encoding="utf-8",
    )

    report = plan_dry_run(
        export_path,
        resolution_cache_path=tmp_path / "missing_resolution.csv",
        details_cache_path=tmp_path / "missing_details.jsonl",
    )

    assert report.input_rows == 2
    assert report.unique_source_records == 2
    assert report.resolution_cache_hits == 0
    assert report.resolution_cache_misses == 2
    assert report.estimated_text_search_calls == 2
    assert report.estimated_place_details_calls == 2
    assert report.to_dict()["search_context"] == "New York, NY"


def test_plan_dry_run_uses_resolution_and_details_caches(tmp_path) -> None:
    export_path = tmp_path / "Restaurants.csv"
    export_path.write_text(
        "\n".join(
            [
                "Title,Note,URL,Tags,Comment",
                "Donovan's Pub,,https://www.google.com/maps/place/Donovan%27s+Pub,,",
                "Rolo's,,https://www.google.com/maps/place/Rolo%27s,,",
            ]
        ),
        encoding="utf-8",
    )
    parsed = parse_google_places_saved_list_csv(export_path)
    first_source_id = parsed.iloc[0]["source_record_id"]

    resolution_cache_path = tmp_path / "place_resolution_cache.csv"
    resolution_cache_path.write_text(
        "\n".join(
            [
                "source_record_id,google_place_id",
                f"{first_source_id},places/donovans",
            ]
        ),
        encoding="utf-8",
    )
    details_cache_path = tmp_path / "place_details_cache.jsonl"
    details_cache_path.write_text(
        json.dumps({"google_place_id": "places/donovans", "payload": {"displayName": "Donovan's Pub"}}),
        encoding="utf-8",
    )

    report = plan_dry_run(
        export_path,
        resolution_cache_path=resolution_cache_path,
        details_cache_path=details_cache_path,
    )

    assert report.resolution_cache_hits == 1
    assert report.resolution_cache_misses == 1
    assert report.cached_google_place_ids == 1
    assert report.details_cache_hits == 1
    assert report.details_cache_misses_for_cached_places == 0
    assert report.estimated_text_search_calls == 1
    assert report.estimated_place_details_calls == 1


def test_read_details_cache_place_ids_accepts_wrapped_and_nested_payloads(tmp_path) -> None:
    details_cache_path = tmp_path / "place_details_cache.jsonl"
    details_cache_path.write_text(
        "\n".join(
            [
                json.dumps({"google_place_id": "places/direct"}),
                json.dumps({"payload": {"id": "places/nested"}}),
                "not json",
            ]
        ),
        encoding="utf-8",
    )

    assert read_details_cache_place_ids(details_cache_path) == {"places/direct", "places/nested"}


def test_text_search_request_only_requests_place_ids() -> None:
    request = build_text_search_id_request("Ursula Bookshop New York, NY", api_key="secret")

    assert request.full_url == "https://places.googleapis.com/v1/places:searchText"
    assert request.get_method() == "POST"
    assert request.headers["X-goog-fieldmask"] == TEXT_SEARCH_ID_FIELD_MASK
    assert request.headers["X-goog-api-key"] == "secret"
    assert json.loads(request.data.decode("utf-8")) == {
        "textQuery": "Ursula Bookshop New York, NY"
    }


def test_place_details_request_only_requests_mapping_fields() -> None:
    request = build_place_details_request("places/abc 123", api_key="secret")

    assert request.full_url == "https://places.googleapis.com/v1/places/places%2Fabc%20123"
    assert request.get_method() == "GET"
    assert request.headers["X-goog-fieldmask"] == PLACE_DETAILS_FIELD_MASK
    assert request.headers["X-goog-api-key"] == "secret"


def test_resolve_place_ids_writes_cache_and_respects_existing_hits(tmp_path) -> None:
    export_path = tmp_path / "New York - Bookstores.csv"
    export_path.write_text(
        "\n".join(
            [
                "Title,Note,URL,Tags,Comment",
                "Ursula Bookshop,,https://www.google.com/maps/place/Ursula+Bookshop,,",
                "Books Are Magic,,https://www.google.com/maps/place/Books+Are+Magic,,",
            ]
        ),
        encoding="utf-8",
    )
    parsed = parse_google_places_saved_list_csv(export_path)
    first_source_id = parsed.iloc[0]["source_record_id"]

    resolution_cache_path = tmp_path / "place_resolution_cache.csv"
    resolution_cache_path.write_text(
        "\n".join(
            [
                "source_record_id,source_system,source_file,source_list_name,input_title,source_url,search_query,google_place_id,match_status",
                f"{first_source_id},google_maps_takeout,New York - Bookstores.csv,New York - Bookstores,Ursula Bookshop,,,places/ursula,top_candidate",
            ]
        ),
        encoding="utf-8",
    )
    calls = []

    def fetcher(query: str, api_key: str):
        calls.append((query, api_key))
        return {"google_place_id": "places/booksaremagic", "match_status": "top_candidate"}

    report = resolve_place_ids(
        export_path,
        api_key="secret",
        resolution_cache_path=resolution_cache_path,
        max_text_search_calls=1,
        fetcher=fetcher,
    )
    cache = read_resolution_cache(resolution_cache_path)

    assert calls == [("Books Are Magic New York, NY", "secret")]
    assert report.cache_hits == 1
    assert report.attempted_text_search_calls == 1
    assert report.resolved == 1
    assert set(cache["google_place_id"]) == {"places/ursula", "places/booksaremagic"}


def test_resolve_place_ids_stops_before_exceeding_call_cap(tmp_path) -> None:
    export_path = tmp_path / "New York - Bookstores.csv"
    export_path.write_text(
        "\n".join(
            [
                "Title,Note,URL,Tags,Comment",
                "Ursula Bookshop,,https://www.google.com/maps/place/Ursula+Bookshop,,",
                "Books Are Magic,,https://www.google.com/maps/place/Books+Are+Magic,,",
            ]
        ),
        encoding="utf-8",
    )

    def fetcher(query: str, api_key: str):
        raise AssertionError("Fetcher should not be called when cap is exceeded.")

    with pytest.raises(ValueError, match="exceed max_text_search_calls"):
        resolve_place_ids(
            export_path,
            api_key="secret",
            resolution_cache_path=tmp_path / "place_resolution_cache.csv",
            max_text_search_calls=1,
            fetcher=fetcher,
        )


def test_resolve_place_ids_requires_api_key(tmp_path, monkeypatch) -> None:
    export_path = tmp_path / "New York - Bookstores.csv"
    export_path.write_text("Title,Note,URL,Tags,Comment\nUrsula Bookshop,,,,", encoding="utf-8")

    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_MAPS_API_KEY"):
        resolve_place_ids(
            export_path,
            api_key=None,
            resolution_cache_path=tmp_path / "place_resolution_cache.csv",
            env_path=tmp_path / "missing.env",
            api_keys_path=tmp_path / "missing_api_keys.yaml",
        )


def test_enrich_place_details_writes_jsonl_cache_and_respects_hits(tmp_path) -> None:
    resolution_cache_path = tmp_path / "place_resolution_cache.csv"
    resolution_cache_path.write_text(
        "\n".join(
            [
                "source_record_id,source_system,source_file,source_list_name,category,input_title,note,tags,comment,source_url,search_query,google_place_id,match_status",
                "src_1,google_maps_takeout,Bookstores.csv,Bookstores,bookstores,Ursula,,,,url,query,places/ursula,top_candidate",
                "src_2,google_maps_takeout,Bookstores.csv,Bookstores,bookstores,Books Are Magic,,,,url,query,places/books,top_candidate",
            ]
        ),
        encoding="utf-8",
    )
    details_cache_path = tmp_path / "place_details_cache.jsonl"
    details_cache_path.write_text(
        json.dumps(
            {
                "google_place_id": "places/ursula",
                "fetched_at": "2026-04-20T00:00:00+00:00",
                "payload": {"displayName": {"text": "Ursula Bookshop"}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    calls = []

    def fetcher(place_id: str, api_key: str):
        calls.append((place_id, api_key))
        return {
            "displayName": {"text": "Books Are Magic"},
            "formattedAddress": "122 Montague St, Brooklyn, NY",
            "location": {"latitude": 40.694, "longitude": -73.992},
        }

    report = enrich_place_details(
        resolution_cache_path=resolution_cache_path,
        details_cache_path=details_cache_path,
        api_key="secret",
        max_details_calls=1,
        fetcher=fetcher,
    )
    cache = read_details_cache(details_cache_path)

    assert calls == [("places/books", "secret")]
    assert report.details_cache_hits == 1
    assert report.attempted_details_calls == 1
    assert set(cache) == {"places/ursula", "places/books"}


def test_build_dim_user_poi_v2_uses_details_and_json_arrays(tmp_path) -> None:
    resolution_cache_path = tmp_path / "place_resolution_cache.csv"
    resolution_cache_path.write_text(
        "\n".join(
            [
                "source_record_id,source_system,source_file,source_list_name,category,input_title,note,tags,comment,source_url,search_query,google_place_id,match_status",
                "src_1,google_maps_takeout,Bookstores.csv,Bookstores,bookstores,Ursula,quiet,tag,note,url1,query,places/ursula,top_candidate",
                "src_2,google_maps_takeout,Bookstores.csv,Favorites,favorites,Ursula,cozy,,,url2,query,places/ursula,top_candidate",
            ]
        ),
        encoding="utf-8",
    )
    details_cache_path = tmp_path / "place_details_cache.jsonl"
    details_cache_path.write_text(
        json.dumps(
            {
                "google_place_id": "places/ursula",
                "fetched_at": "2026-04-20T00:00:00+00:00",
                "payload": {
                    "displayName": {"text": "Ursula Bookshop"},
                    "formattedAddress": "1016 Union St, Brooklyn, NY",
                    "location": {"latitude": 40.674, "longitude": -73.963},
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    dim = build_dim_user_poi_v2(
        resolution_cache_path=resolution_cache_path,
        details_cache_path=details_cache_path,
    )
    row = dim.iloc[0]

    assert len(dim) == 1
    assert row["poi_id"].startswith("poi_")
    assert row["name"] == "Ursula Bookshop"
    assert row["address"] == "1016 Union St, Brooklyn, NY"
    assert row["lat"] == 40.674
    assert row["lon"] == -73.963
    assert json.loads(row["source_list_names"]) == ["Bookstores", "Favorites"]
    assert json.loads(row["categories"]) == ["bookstores", "favorites"]
    assert json.loads(row["note"]) == ["quiet", "cozy"]


def test_pipeline_writes_dim_user_poi_v2(tmp_path) -> None:
    export_path = tmp_path / "Bookstores.csv"
    export_path.write_text(
        "Title,Note,URL,Tags,Comment\nUrsula Bookshop,quiet,url,tag,comment\n",
        encoding="utf-8",
    )
    database_path = tmp_path / "nyc_property_finder.duckdb"

    def resolve_fetcher(query: str, api_key: str):
        return {"google_place_id": "places/ursula", "match_status": "top_candidate"}

    def details_fetcher(place_id: str, api_key: str):
        return {
            "displayName": {"text": "Ursula Bookshop"},
            "formattedAddress": "1016 Union St, Brooklyn, NY",
            "location": {"latitude": 40.674, "longitude": -73.963},
        }

    # Run the lower-level pieces with fakes, then let the pipeline build/write
    # from those caches without making additional calls.
    resolution_cache_path = tmp_path / "place_resolution_cache.csv"
    details_cache_path = tmp_path / "place_details_cache.jsonl"
    resolve_place_ids(
        export_path,
        api_key="secret",
        resolution_cache_path=resolution_cache_path,
        fetcher=resolve_fetcher,
    )
    enrich_place_details(
        resolution_cache_path=resolution_cache_path,
        details_cache_path=details_cache_path,
        api_key="secret",
        fetcher=details_fetcher,
    )

    report = run_google_places_poi(
        export_path,
        database_path=database_path,
        resolution_cache_path=resolution_cache_path,
        details_cache_path=details_cache_path,
        max_text_search_calls=0,
        max_details_calls=0,
        api_key="secret",
    )

    with DuckDBService(database_path, read_only=True) as duckdb_service:
        rows = duckdb_service.query_df("SELECT name, address, lat, lon FROM property_explorer_gold.dim_user_poi_v2")

    assert report.dim_rows == 1
    assert report.dim_with_coordinates == 1
    assert rows.iloc[0]["name"] == "Ursula Bookshop"
