# User Guide

Short overview of how to use the Repo and the Streamlit Apps.

## Add Google Maps Saved Places

Use this flow when you have a single Google Takeout saved-list CSV, such as:

```text
data/raw/google_maps/New York - Bookstores.csv
```

The pipeline turns that CSV into a deduplicated, geocoded table:

```text
property_explorer_gold.dim_user_poi_v2
```

### One-Time Setup

Create a local `.env` file in the repo root:

```bash
printf 'GOOGLE_MAPS_API_KEY=your_google_maps_key_here\n' > .env
chmod 600 .env
```

Enable **Places API (New)** in the Google Cloud project for that key.

The key is read from `.env`, and `.env` is ignored by git.

### Run One CSV

From the repo root:

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.ingest_google_places_poi "data/raw/google_maps/New York - Bookstores.csv"
```

To use another Google Takeout CSV, replace the quoted path with your file:

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.ingest_google_places_poi "data/raw/google_maps/YOUR_FILE.csv"
```

### What The Pipeline Does

The run has three steps:

1. Resolves each CSV row to a Google `place_id`.
2. Fetches minimal Place Details for each unique place ID.
3. Writes the deduplicated table to DuckDB.

The API calls are cache-first. Re-running the same CSV should make zero new API
calls unless new places were added.

### Fields Requested From Google

Text Search asks only for:

```text
places.id
```

Place Details asks only for:

```text
displayName
formattedAddress
location
```

The pipeline does not request reviews, ratings, hours, photos, or other richer
metadata.

### Outputs

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
property_explorer_gold.dim_user_poi_v2
```

### Guardrails

Defaults:

```text
max Text Search calls: 50
max Place Details calls: 50
```

If a run would exceed those caps, it stops before making the extra calls.

You can override the caps:

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.ingest_google_places_poi "data/raw/google_maps/New York - Bookstores.csv" --max-text-search-calls 100 --max-details-calls 100
```

### Check The Result

Open the summary:

```bash
cat data/interim/google_places/place_pipeline_summary.json
```

Review duplicate or missing-coordinate warnings:

```bash
cat data/interim/google_places/place_pipeline_qa.csv
```

Quick table count:

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

## FAQs

### How do I add new Geographic areas (Counties, Tracts, Places, etc)?

### How do I add new Points of Interest?

Use the Google Maps Saved Places flow above for a single Google Takeout CSV.
Directory-wide ingestion and multi-source merging are later improvements.
