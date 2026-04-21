# Pipeline Plan

This is the operational build plan for the local NYC Property Finder data
platform. The MVP pipeline is file-backed and deterministic: raw/private inputs
stay under `data/raw` or ignored local config, build modules normalize those
inputs, and app-ready outputs land in DuckDB under `property_explorer_gold`.

Use `docs/data_model.md` for table contracts and `docs/source_inventory.md` for
source decisions, URLs, and caveats.

## Build Inputs

The runbook assumes these local inputs exist or have been configured:

| Input | Default path/config | Used by |
| --- | --- | --- |
| App settings | `config/settings.yaml` | Database path, default user, map center, target boroughs. |
| Source config | `config/data_sources.yaml`, falling back to `config/data_sources.example.yaml` | Raw source paths and private Metro Deep Dive DB path. |
| DDL | `sql/ddl/001_gold_tables.sql` | DuckDB schema/table creation. |
| Tract/NTA equivalency | `data/raw/geography/tract_to_nta_equivalency.csv` | `dim_tract_to_nta`. |
| Census tract geometry | `data/raw/geography/census_tracts.geojson` | Neighborhood Explorer and property tract assignment. |
| Subway GTFS/stops | `data/raw/transit/gtfs_subway.zip` or `data/raw/transit/subway_stops.csv` | `dim_subway_stop`. |
| Google Maps export | `data/raw/google_maps/saved_places.kml`, `.json`, `.csv`, or CSV directory | `dim_user_poi`. |
| Listing file | `data/raw/listings_sample.csv`; future default `data/raw/property_listings.csv` | `dim_property_listing`. |
| Metro Deep Dive features | `sources.metro_deep_dive_tract_features.source_database_path` in local config | `fct_tract_features`, `fct_nta_features`. |

## Local Build Order

Run from the repository root. Activate the project virtual environment first if
you use one.

```bash
source .venv/bin/activate
```

1. Initialize DuckDB schema.

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.init_database
```

2. Build the tract-to-NTA mapping from the selected NYC equivalency CSV.

```bash
PYTHONPATH=src .venv/bin/python -c "from nyc_property_finder.pipelines.build_tract_to_nta import run_equivalency; run_equivalency('data/raw/geography/tract_to_nta_equivalency.csv', 'data/processed/nyc_property_finder.duckdb')"
```

Fallback when the equivalency CSV is unavailable: use tract and NTA geometries
with centroid assignment.

```bash
PYTHONPATH=src .venv/bin/python -c "from nyc_property_finder.pipelines.build_tract_to_nta import run; run('data/raw/geography/census_tracts.geojson', 'data/raw/geography/nta_boundaries.geojson', 'data/processed/nyc_property_finder.duckdb')"
```

3. Ingest subway stops.

```bash
PYTHONPATH=src .venv/bin/python -c "from nyc_property_finder.pipelines.ingest_subway_stops import run; run('data/raw/transit/gtfs_subway.zip', 'data/processed/nyc_property_finder.duckdb')"
```

Use `data/raw/transit/subway_stops.csv` in the same command if working from a
normalized station file instead of the GTFS zip.

4. Ingest Google Maps POIs.

```bash
PYTHONPATH=src .venv/bin/python -c "from nyc_property_finder.pipelines.ingest_google_maps import run; run('data/raw/google_maps/saved_places.kml', 'data/processed/nyc_property_finder.duckdb')"
```

The same entrypoint accepts JSON, saved-list CSV, or a directory of saved-list
CSVs. CSV exports that lack coordinates can use the NYC GeoSearch-backed
geocode cache/quarantine path.

5. Ingest property listings.

```bash
PYTHONPATH=src .venv/bin/python -c "from nyc_property_finder.pipelines.ingest_property_file import run; run('data/raw/listings_sample.csv', 'data/processed/nyc_property_finder.duckdb', source='manual_csv')"
```

Rows without coordinates can enter the listing geocode cache/quarantine path.
Rows still missing coordinates after geocoding are dropped from the normalized
gold listing table and should be reviewed before scoring.

6. Build tract and NTA feature tables.

```bash
PYTHONPATH=src .venv/bin/python -c "from nyc_property_finder.pipelines.build_neighborhood_features import run_metro_deep_dive; run_metro_deep_dive('data/processed/nyc_property_finder.duckdb', '/path/to/local/metro_deep_dive.duckdb')"
```

The Metro Deep Dive database path should come from ignored
`config/data_sources.yaml` in regular use. If the local source does not expose
NYC tract metrics yet, the current pipeline can still materialize Brooklyn and
Manhattan tract/NTA rows with null metric values so Neighborhood Explorer can
validate geography before demographic coverage is solved.

7. Build property context and scores.

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.build_property_context
```

Override paths when needed:

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.build_property_context --database-path data/processed/nyc_property_finder.duckdb --tract-path data/raw/geography/census_tracts.geojson --tract-id-col GEOID
```

8. Run validation tests.

```bash
.venv/bin/pytest
```

For a faster focused check while iterating on data contracts:

```bash
.venv/bin/pytest tests/test_schema.py tests/test_tract_to_nta.py tests/test_neighborhood_features.py tests/test_property_context_pipeline.py tests/test_base_map_app.py
```

9. Launch the apps.

```bash
PYTHONPATH=src .venv/bin/streamlit run app/streamlit_app_v2.py
```

```bash
PYTHONPATH=src .venv/bin/streamlit run app/neighborhood_qa_app.py
```

```bash
PYTHONPATH=src .venv/bin/streamlit run app/streamlit_app.py
```

## Dependency Order

| Step | Writes | Must run after | Notes |
| --- | --- | --- | --- |
| Init database | Empty gold tables | None | Re-runnable; creates tables if missing. |
| Tract/NTA mapping | `dim_tract_to_nta` | Init database | Required by Neighborhood Explorer, NTA features, and property context. |
| Subway ingest | `dim_subway_stop` | Init database | Required for mobility context. |
| POI ingest | `dim_user_poi` | Init database | Required for personal fit context. |
| Listing ingest | `dim_property_listing` | Init database | Required before property context. |
| Neighborhood features | `fct_tract_features`, `fct_nta_features` | Tract/NTA mapping | Can produce explicit null metric rows when source coverage is missing. |
| Property context | `fct_property_context` | Listings, mapping, subway, POIs, features | Primary table for the property explorer. |
| Neighborhood Explorer | None | Mapping, features, tract geometry | Can render boundaries with null metrics. |
| Streamlit property explorer | User-authored shortlist rows | Context, POIs, subway, NTA features | Shortlist rows should not be replaced during rebuilds. |

## Current Gaps

- Most ingestion modules expose Python `run(...)` functions, not full command
  line interfaces. The one-liners above are the operational path for now.
- `config/data_sources.yaml` is intentionally ignored/private. Keep
  `config/data_sources.example.yaml` current so new machines can bootstrap.
- The Metro Deep Dive source table/view selection is still an open data-source
  decision.
- The build is not yet orchestrated by a single CLI command. A thin CLI wrapper
  should eventually make the build order repeatable without long one-liners.
