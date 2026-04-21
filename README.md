# NYC Property Finder

NYC Property Finder is a local Python data product for evaluating rental and
purchase listings with neighborhood, transit, and personal points-of-interest
context.

The project has three main pieces:

- A file-backed data platform that loads raw local sources into DuckDB.
- Python pipelines that normalize sources, build geography/context tables, and
  score listings.
- Two Streamlit apps: Property Explorer for listings and Neighborhood Explorer
  for tract/neighborhood context.

## Documentation

Start with the docs index:

- `docs/README.md`: documentation map and ownership guide.
- `docs/architecture.md`: system architecture and data flow.
- `docs/data_model.md`: DuckDB gold table contracts, source/build manifest, and
  QA matrix.
- `docs/pipeline_plan.md`: operational build order and commands.
- `docs/source_inventory.md`: raw source URLs, path conventions, and caveats.
- `docs/app/property_explorer_app.md`: Property Explorer app behavior.
- `docs/app/neighborhood_explorer_app.md`: Neighborhood Explorer app behavior.

## Setup

Create an environment, install dependencies, and install the package in editable
mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

`config/data_sources.yaml` is local-only because it can contain absolute paths
and private source locations. Start from the tracked template:

```bash
cp config/data_sources.example.yaml config/data_sources.yaml
```

Update `config/data_sources.yaml` with local source paths before running a full
data refresh. App defaults such as the DuckDB path and local user ID live in
`config/settings.yaml`.

## Initialize The Database

Initialize DuckDB before loading or rebuilding data:

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.init_database
```

This creates the database configured in `config/settings.yaml` and runs the DDL
under `sql/ddl/`. The main app-facing schema is `property_explorer_gold`.

## Update Data

The MVP data build is local and file-backed. Raw/private inputs stay under
`data/raw`, ignored local config, or other local-only paths. The complete build
order is documented in `docs/pipeline_plan.md`; the short version is:

1. Initialize the database.
2. Build tract-to-NTA mapping.
3. Ingest subway stops.
4. Ingest Google Maps POIs.
5. Ingest property listings.
6. Build tract and NTA feature tables.
7. Build property context and scores.
8. Run tests or focused QA checks.

Common pipeline entrypoints:

| Task | Entry point |
| --- | --- |
| Initialize schema | `nyc_property_finder.pipelines.init_database` |
| Tract/NTA mapping | `nyc_property_finder.pipelines.build_tract_to_nta` |
| Subway stops | `nyc_property_finder.pipelines.ingest_subway_stops` |
| Google Maps POIs | `nyc_property_finder.pipelines.ingest_google_maps` |
| Property listings | `nyc_property_finder.pipelines.ingest_property_file` |
| Neighborhood features | `nyc_property_finder.pipelines.build_neighborhood_features` |
| Property context | `nyc_property_finder.pipelines.build_property_context` |

Most ingestion modules currently expose Python `run(...)` functions rather than
full command line interfaces. Use the exact one-liners in
`docs/pipeline_plan.md` for a full refresh.

Run the test suite after data or contract changes:

```bash
.venv/bin/pytest
```

## Open The Streamlit Apps

Run each app from the repository root in its own terminal. Use the project
virtual environment and set `PYTHONPATH=src` so Streamlit can import the local
`nyc_property_finder` package even before an editable install is refreshed.

### Neighborhood Explorer

Neighborhood Explorer is the geography and demographic foundation app. It reads
tract geometry, tract-to-NTA mapping, tract features, and NTA features.

```bash
PYTHONPATH=src .venv/bin/streamlit run app/streamlit_app_v2.py
```

### Neighborhood Data QA

Neighborhood Data QA is the coverage and source-readiness companion app for the
neighborhood foundation. Use it to inspect metric coverage, expected gold-table
row counts, and configured source paths.

```bash
PYTHONPATH=src .venv/bin/streamlit run app/neighborhood_qa_app.py
```

### Property Explorer

Property Explorer is the listing review app. It reads property context, POIs,
subway stops, NTA features, and the local shortlist table.

```bash
PYTHONPATH=src .venv/bin/streamlit run app/streamlit_app.py
```

If you see `ModuleNotFoundError: No module named 'nyc_property_finder'`, you are
probably using a global Streamlit executable or an environment where this
package is not installed. Re-run the command above from the repository root, or
refresh the editable install with `.venv/bin/pip install -e .`.

## Close The Streamlit Apps

If Streamlit is running in the foreground, close the app by pressing
`Ctrl+C` in the terminal where it is running.

If you started Streamlit in the background or lost the terminal, find running
Streamlit processes:

```bash
pgrep -af streamlit
```

Then stop the specific process by PID:

```bash
kill <PID>
```

Use `pkill -f streamlit` only when you intentionally want to stop every
Streamlit process on your machine.

## Project Layout

```text
app/                            Streamlit entry points
config/                         YAML settings and source metadata
data/raw/                       Raw local source files
data/interim/                   Temporary pipeline outputs and geocode caches
data/processed/                 DuckDB database and processed artifacts
docs/                           Documentation and planning notes
sql/                            DDL and SQL build assets
src/nyc_property_finder/        Python package
tests/                          Unit and pipeline helper tests
```
