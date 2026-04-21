# Sprint 2 Foundation Build Runbook

This runbook rebuilds the current Property Explorer foundation tables in the
local DuckDB database.

## Inputs

- Listings: `data/raw/listings_sample.csv`
- Google Maps saved-list CSVs: `data/raw/google_maps/*.csv`
- Tract/NTA equivalency:
  `data/raw/geography/tract_to_nta_equivalency.csv`
- Subway GTFS: `data/raw/transit/gtfs_subway.zip`
- Metro Deep Dive DuckDB:
  `/Users/danberle/Documents/projects/data/duckdb/metro_deep_dive.duckdb`

## Download Public Sources

```bash
mkdir -p data/raw/geography data/raw/transit
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
from urllib.request import urlretrieve
from nyc_property_finder.pipelines.ingest_subway_stops import download_subway_gtfs

tract_url = "https://data.cityofnewyork.us/api/views/hm78-6dwm/rows.csv?accessType=DOWNLOAD"
tract_path = Path("data/raw/geography/tract_to_nta_equivalency.csv")
urlretrieve(tract_url, tract_path)
download_subway_gtfs("data/raw/transit/gtfs_subway.zip")
PY
```

## Build Foundation Tables

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.init_database
PYTHONPATH=src .venv/bin/python - <<'PY'
from nyc_property_finder.pipelines.ingest_property_file import run as run_listings
from nyc_property_finder.pipelines.ingest_google_maps import run as run_poi
from nyc_property_finder.pipelines.build_tract_to_nta import run_equivalency
from nyc_property_finder.pipelines.ingest_subway_stops import run as run_subway
from nyc_property_finder.pipelines.build_neighborhood_features import run_metro_deep_dive

db = "data/processed/nyc_property_finder.duckdb"
metro = "/Users/danberle/Documents/projects/data/duckdb/metro_deep_dive.duckdb"

run_listings("data/raw/listings_sample.csv", db, source="streeteasy_saved")
run_poi("data/raw/google_maps", db)
run_equivalency("data/raw/geography/tract_to_nta_equivalency.csv", db)
run_subway("data/raw/transit/gtfs_subway.zip", db)
run_metro_deep_dive(db, metro)
PY
```

## QA Counts

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
from nyc_property_finder.services.duckdb_service import DuckDBService

db = "data/processed/nyc_property_finder.duckdb"
tables = [
    "dim_property_listing",
    "dim_user_poi",
    "dim_tract_to_nta",
    "dim_subway_stop",
    "fct_tract_features",
    "fct_nta_features",
]
with DuckDBService(db, read_only=True) as svc:
    for table in tables:
        count = svc.query_df(f"SELECT COUNT(*) AS n FROM property_explorer_gold.{table}")["n"].iloc[0]
        print(f"{table}: {count}")
PY
```

Current expected counts after the Sprint 2 build:

| Table | Count | Notes |
| --- | ---: | --- |
| `dim_property_listing` | 22 | 19 rentals, 3 sales; all geocoded. |
| `dim_user_poi` | 206 | Resolved from Google Maps saved-list CSVs using NYC GeoSearch. |
| `dim_tract_to_nta` | 2,327 | NYC Open Data `hm78-6dwm` equivalency. |
| `dim_subway_stop` | 496 | MTA regular subway static GTFS. |
| `fct_tract_features` | 1,115 | Brooklyn and Manhattan tract feature rows. Metric values are null because the local Metro Deep Dive source does not currently expose NYC tract metrics. |
| `fct_nta_features` | 108 | Brooklyn and Manhattan NTA feature rows aggregated from tract rows. Metric values are null for the same source-coverage reason. |

## Notes

- Listing and POI geocoding use NYC GeoSearch and write caches/quarantines under
  `data/interim/geocoding/`.
- Google Places API is Post-MVP.
- Geometry alignment decision: use NYC Open Data `hm78-6dwm` as the authoritative
  tract/NTA equivalency and NYC DCP/ArcGIS 2020 census tract and NTA boundary
  files for geometry when Sprint 3 needs map polygons/property spatial joins.
