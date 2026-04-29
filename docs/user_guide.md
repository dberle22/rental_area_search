# User Guide

Short overview of common curated POI workflows in the repo.

## Curated POI Overview

Curated POIs currently have one active ingestion path:

- Google Takeout saved lists under `data/raw/google_maps/poi_nyc/`

The active implementation now lives under:

```text
src/nyc_property_finder/curated_poi/google_takeout/
```

The preferred CLI entry point is:

```text
nyc_property_finder.pipelines.ingest_curated_poi_google_takeout
```

This pipeline writes:

```text
property_explorer_gold.dim_user_poi_v2
```

## One-Time Setup

Create a local `.env` file in the repo root:

```bash
printf 'GOOGLE_MAPS_API_KEY=your_google_maps_key_here\n' > .env
chmod 600 .env
```

Enable **Places API (New)** in the Google Cloud project for that key.

The key is read from `.env`, and `.env` is ignored by git.

## Update POI Categories

Use this workflow whenever you want to add or adjust curated taxonomy.

### Where taxonomy lives

- Config rules: `config/poi_categories.yaml`
- Reference documentation: `docs/poi_categories.md`

### What to update

1. Update `config/poi_categories.yaml`.
2. Add or revise the file-level rule under `curated_taxonomy.files`.
3. If needed, add or revise `tag_aliases` used to derive subcategory or level-3 descriptors.
4. Update `docs/poi_categories.md` so the documented taxonomy matches the config.

### Taxonomy model

- `category`: top-level group such as `restaurants`, `bars`, `music_venues`
- `subcategory`: one stable, primary filter bucket
- `detail_level_3`: flexible descriptor layer that can hold one or many tags

Examples:

- `restaurants / japanese / ramen|sushi|izakaya`
- `restaurants / sandwiches / deli|italian`
- `bars / irish_pub /`

## Export Google Takeout

Use this flow when your places are saved as Google Maps lists.

1. Go to Google Takeout: https://takeout.google.com/
2. Deselect all products.
3. Select Saved.
4. Create a one-time export.
5. Download the zip when the email arrives.
6. Put the CSVs you want to ingest under `data/raw/google_maps/poi_nyc/`.

## Dry Run A Batch

Use dry run before any live ingestion. It does not hit the API and does not
write DuckDB.

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.ingest_curated_poi_google_takeout \
  --input-dir data/raw/google_maps/poi_nyc \
  --dry-run
```

Dry-run reports:

- per-file row counts
- category assignments
- subcategory assignments
- level-3 descriptor values
- estimated Text Search calls
- estimated Place Details calls

## Run A Batch

Use this to process the full curated Google Takeout directory.

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.ingest_curated_poi_google_takeout \
  --input-dir data/raw/google_maps/poi_nyc
```

This flow:

1. Parses every CSV in `data/raw/google_maps/poi_nyc/`
2. Resolves rows to Google `place_id`s
3. Fetches minimal Place Details for unique places
4. Writes the current batch into `property_explorer_gold.stg_user_poi_google_takeout`
5. Promotes that staged batch into canonical `property_explorer_gold.dim_user_poi_v2`

The API calls are cache-first. Re-running the same inputs should make zero new
API calls unless the inputs changed.

## Run One CSV

Use this while iterating on one curated file.

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.ingest_curated_poi_google_takeout \
  data/raw/google_maps/poi_nyc/poi_bookstores_nyc.csv
```

## Guardrails

Defaults:

```text
max Text Search calls: 50
max Place Details calls: 50
```

If a run would exceed those caps, it stops before making the extra calls.

Override when needed:

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.ingest_curated_poi_google_takeout \
  --input-dir data/raw/google_maps/poi_nyc \
  --max-text-search-calls 100 \
  --max-details-calls 100
```

## Outputs

Intermediate caches:

```text
data/interim/google_places/place_resolution_cache.csv
data/interim/google_places/place_details_cache.jsonl
```

Run summary and quick QA:

```text
data/interim/google_places/place_pipeline_summary.json
data/interim/google_places/place_pipeline_qa.csv
```

DuckDB table:

```text
data/processed/nyc_property_finder.duckdb
property_explorer_gold.stg_user_poi_google_takeout
property_explorer_gold.dim_user_poi_v2
```

## Check The Result

Open the summary:

```bash
cat data/interim/google_places/place_pipeline_summary.json
```

Review duplicate or missing-coordinate warnings:

```bash
cat data/interim/google_places/place_pipeline_qa.csv
```

Quick row count:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
from nyc_property_finder.services.duckdb_service import DuckDBService

with DuckDBService("data/processed/nyc_property_finder.duckdb", read_only=True) as db:
    print(db.query_df("""
        SELECT
            COUNT(*) AS rows,
            COUNT(*) FILTER (WHERE lat IS NOT NULL AND lon IS NOT NULL) AS rows_with_coordinates
        FROM property_explorer_gold.dim_user_poi_v2
    """))
PY
```

## Compatibility Note

The older CLI path still exists:

```text
nyc_property_finder.pipelines.ingest_google_places_poi
```

But new documentation should use:

```text
nyc_property_finder.pipelines.ingest_curated_poi_google_takeout
```
