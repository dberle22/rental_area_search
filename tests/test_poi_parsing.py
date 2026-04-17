import json

from nyc_property_finder.pipelines.ingest_google_maps import ingest_google_maps
from nyc_property_finder.transforms.poi import normalize_category


def test_normalize_category_uses_keyword_mapping() -> None:
    assert normalize_category("Tiny Coffee Bar") == "bars"
    assert normalize_category("Prospect Park") == "parks"
    assert normalize_category("Somewhere Unknown") == "other"


def test_ingest_google_maps_json_parses_and_normalizes(tmp_path) -> None:
    export_path = tmp_path / "saved_places.json"
    export_path.write_text(
        json.dumps(
            {
                "places": [
                    {
                        "name": "Neighborhood Coffee",
                        "list_name": "Favorites",
                        "location": {"lat": 40.7, "lng": -73.9},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    poi = ingest_google_maps(export_path)

    assert len(poi) == 1
    assert poi.iloc[0]["category"] == "coffee_shops"
    assert poi.iloc[0]["source_list_name"] == "Favorites"
    assert poi.iloc[0]["poi_id"].startswith("poi_")
