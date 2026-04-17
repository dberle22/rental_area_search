# NYC Property Finder MVP Build Plan

## Current Repo Assessment

The repository is a working Python scaffold for a local NYC property discovery data product, not yet a complete MVP. It has a `src/` package layout, YAML config, starter DuckDB service, geospatial helpers, placeholder pipelines, a minimal Streamlit/PyDeck app, notebooks, docs, SQL DDL, and five passing unit tests when run with `.venv/bin/pytest`.

Important current facts:

- The shell does not find `pytest` globally; use `.venv/bin/pytest` or activate `.venv`.
- The directory is not currently a Git repository.
- `data/raw`, `data/interim`, and `data/processed` contain only `.gitkeep` files; no real local source data is present.
- Existing DDL only creates `gold.dim_user_poi` and `gold.dim_property_listing`, while code also expects tables such as `gold.dim_tract_to_nta`, `gold.fct_tract_features`, and eventually `gold.fct_property_context`.
- `build_tract_to_nta.py`, Google Maps POI parsing, hashing, GeoPandas point helpers, simple scoring, and table-writing helpers are usable starter code.
- Property ingestion is skeletal: StreetEasy and RentHop return empty structured data, with no scraping, API, CSV import, or fixture-backed ingestion path.
- Neighborhood features are placeholder-only unless an already-shaped ACS dataframe is passed in memory.
- Property context has useful transform functions but no persisted pipeline entry point that reads source tables from DuckDB and writes `fct_property_context`.
- The Streamlit app only maps properties and POIs from DuckDB. It does not yet show NTA/tract layers, subway access, neighborhood metrics, score breakdowns, shortlist, or property detail views.

## MVP Product Definition

The MVP should let a user load a small NYC-focused dataset, view property listings on a map, compare them against personal saved places and subway access, and sort/filter by a transparent fit score.

MVP user workflow:

1. Configure local source paths and target boroughs.
2. Build a local DuckDB database from fixture or downloaded NYC geography, transit, POI, neighborhood, and listing inputs.
3. Open Streamlit and see properties, POIs, subway context, neighborhood assignment, and score components.
4. Filter by price, beds, listing type, borough or NTA, POI category, and score threshold.
5. Select a property and inspect address, price, beds/baths, NTA, nearest subway, nearby POIs, and score breakdown.

MVP non-goals:

- Production scraping at scale.
- Real-time listing refresh.
- Advanced ML pricing or recommendation models.
- Full NYC data completeness beyond enough borough coverage for a credible demo.
- Multi-user accounts or cloud deployment.

## Engineering Principles

- Make the first end-to-end path fixture-backed and deterministic before adding fragile external acquisition.
- Keep DuckDB table contracts explicit in SQL and tests; avoid hidden in-memory-only schemas.
- Prefer source adapters that normalize CSV/GeoJSON/KML/JSON files before implementing website scraping.
- Keep geospatial calculations in GeoPandas/Shapely until there is a clear reason to use DuckDB spatial extensions.
- Preserve simple, transparent scoring and expose score components in the app.
- Add tests around transforms and pipeline table outputs, not around visual polish alone.
- Treat notebooks as exploration records; production logic should live under `src/nyc_property_finder`.

## Sprint Plan

### Sprint 1: Make The Scaffold Reproducible

Goal: Ensure a future agent can install, test, and build a minimal local database without guessing.

Tasks:

- Add complete gold DDL for expected MVP tables: `dim_tract_to_nta`, `dim_subway_stop`, `fct_tract_features`, `fct_nta_features` if used, and `fct_property_context`.
- Add a small command or module entry point for initializing DuckDB schemas from `sql/ddl`.
- Add tiny fixture files under tests or a non-production sample-data location for geography, POI, subway, ACS-like features, and listings.
- Add tests proving DDL initialization and DuckDB write/read behavior.
- Document the canonical local commands in README or a dev note after the plan is implemented.

Deliverables:

- A repeatable database initialization path.
- Fixture-backed tests that do not require external downloads.
- Clear table contracts matching the code.

Acceptance criteria:

- `.venv/bin/pytest` passes.
- A fresh `data/processed/nyc_property_finder.duckdb` can be created from code.
- Every table the app or pipelines expect is either created or intentionally deferred.

Dependencies:

- Existing `DuckDBService`.
- Current config files and DDL folder.

### Sprint 2: Implement File-Based Listing Ingestion

Goal: Make property listings usable without depending on live scraping.

Tasks:

- Add a CSV/JSON property listing ingestion pipeline using `normalize_property_listings`.
- Extend `config/data_sources.yaml` with a local listings source path.
- Add validation for required listing fields and coordinate availability.
- Define deduplication behavior for repeated source listings.
- Keep StreetEasy/RentHop scraper classes as future adapters, but do not make MVP dependent on them.

Deliverables:

- `gold.dim_property_listing` populated from a local file.
- Fixture coverage for valid rows, missing coordinates, duplicate source IDs, and numeric coercion.

Acceptance criteria:

- A sample listings file can be loaded into DuckDB.
- Normalized listings have stable `property_id` values.
- Invalid rows are either rejected with clear errors or quarantined in a documented way.

Dependencies:

- Sprint 1 DDL and fixture conventions.

### Sprint 3: Geography, Transit, And POI Tables

Goal: Build the spatial context tables needed for property enrichment.

Tasks:

- Finalize expected source schemas for census tracts and NTA boundaries in `config/data_sources.yaml`.
- Harden `build_tract_to_nta.py` against common NYC source column names or add config-driven column mapping.
- Add a subway stop ingestion pipeline from CSV, including stop ID, name, lines, lat, and lon.
- Update Google Maps ingestion to pass configured `poi_categories.yaml` keywords into normalization.
- Add tests for KML/JSON POI parsing, category config use, tract-to-NTA mapping, and subway line counts.

Deliverables:

- `gold.dim_tract_to_nta`, `gold.dim_user_poi`, and `gold.dim_subway_stop` populated from local files.
- Source schema notes for each required geography/transit/POI input.

Acceptance criteria:

- Fixture geography can assign points to tract/NTA.
- POIs preserve source list names and configured categories.
- Subway stops expose line counts needed for mobility scoring.

Dependencies:

- Sprint 1 DDL.
- Local or fixture source files.

### Sprint 4: Neighborhood Features And Scoring

Goal: Produce transparent neighborhood and property fit scores from persisted tables.

Tasks:

- Implement file-based ACS-like feature ingestion with explicit column mapping.
- Decide whether crime proxy is in MVP; if yes, implement a simple tract-level input table rather than spatial incident processing.
- Add a persisted `build_property_context.run(...)` entry point that reads DuckDB tables and writes `gold.fct_property_context`.
- Ensure `poi_category_counts` is stored in a DuckDB-friendly representation such as JSON text.
- Add tests for score formulas, missing data behavior, and persisted context output.

Deliverables:

- `gold.fct_tract_features` and `gold.fct_property_context` populated end to end.
- Score components available for app display.

Acceptance criteria:

- Every property with coordinates receives tract/NTA fields where geometry coverage allows.
- Every property receives neighborhood, mobility, personal fit, and total score fields.
- Missing POI, subway, or feature data degrades gracefully to low or neutral scores as documented.

Dependencies:

- Sprints 2 and 3.
- Finalized scoring weights config.

### Sprint 5: MVP Streamlit App

Goal: Turn the local database into a useful property review interface.

Tasks:

- Add table availability checks and clear empty states.
- Add filters for price, beds, listing type, NTA, POI category, and minimum score.
- Map property and POI layers; add subway stops if data exists.
- Add property detail panel with score breakdown, nearest subway, nearby POI summary, and listing URL.
- Add neighborhood summary metrics for the selected property or NTA.
- Add a simple local shortlist using Streamlit session state.

Deliverables:

- One usable Streamlit app screen for map exploration and property detail.
- Optional secondary page for shortlist/comparison only if it stays small.

Acceptance criteria:

- `streamlit run app/streamlit_app.py` opens an app that works against the fixture-built database.
- Selecting or filtering properties updates visible metrics and detail content.
- The app remains useful when optional tables are empty.

Dependencies:

- Sprint 4 context table.

### Sprint 6: Source Acquisition And MVP Hardening

Goal: Replace fixtures with documented NYC source downloads and prepare the repo for sustained development.

Tasks:

- Add acquisition notes or scripts for NYC tracts, NTA boundaries, subway stops, and ACS-derived features.
- Decide whether property listings come from manual CSV export, API partner, scraped source, or user-provided file for MVP.
- Add pipeline orchestration command that runs the MVP build sequence from config.
- Add linting/formatting checks if desired, matching existing Ruff config.
- Add minimal CI once the directory is initialized as a Git repository.

Deliverables:

- Source acquisition documentation.
- One command or documented sequence for rebuilding DuckDB.
- Stable smoke test for the full local build.

Acceptance criteria:

- A new developer can reproduce the MVP database and app from documented inputs.
- Fragile or legally sensitive scraping work is isolated behind adapters and not required for demo success.

Dependencies:

- Prior sprints.
- Open decision on listing source.

## Data Dependencies

Required for MVP:

- Census tract geometry with tract IDs and polygons.
- NTA geometry with NTA IDs, names, and polygons.
- Subway stops with stop ID, stop name, served lines, lat, and lon.
- Google Maps saved places export in KML or JSON.
- Property listings in CSV/JSON with source listing ID, address, lat, lon, price, beds, baths, listing type, and URL.
- Tract-level neighborhood features including median income, median rent, median home value, percent bachelor's plus, median age, and optional crime proxy.

Recommended first implementation sources:

- Use checked-in test fixtures for automated tests.
- Use local raw files under `data/raw` for real runs.
- Prefer manual or exported listings file for MVP until scraping/data access terms are confirmed.

## Open Decisions

- Which property listing source is acceptable for MVP: manual CSV, partner/API, StreetEasy scraper, RentHop scraper, or another source.
- Whether the MVP should include Brooklyn and Manhattan only, or fixture/demo coverage first.
- Whether crime proxy belongs in MVP or should remain a placeholder until a defensible source is chosen.
- Whether `fct_nta_features` is required for the app or can be deferred behind tract-level features plus NTA names.
- How to store geometry long term: WKT in DuckDB for starter portability, GeoParquet sidecars, or DuckDB spatial extension.
- Whether Google Maps category matching should remain keyword-based or accept user-edited category overrides.
- Whether shortlist state should be local session-only for MVP or persisted to DuckDB.

## Risks And Mitigations

- Property scraping risk: website terms, anti-bot behavior, and schema churn can stall the MVP. Mitigate by making file-based listing ingestion the primary MVP path.
- Source schema drift: NYC and Census field names may differ from config assumptions. Mitigate with source-specific mapping config and fixture tests.
- Geospatial performance: all-pairs distance helpers are fine for small MVP data but may not scale. Mitigate later with spatial indexes, bounding boxes, or DuckDB spatial.
- Empty-data app experience: current app hides most value without populated tables. Mitigate with table checks, fixtures, and clear setup state.
- Score credibility: simple scores can look more precise than they are. Mitigate by showing component scores and documenting formula assumptions.
- Environment fragility: pytest is not globally available and the folder is not a Git repo. Mitigate with setup docs and eventual Git/CI initialization.

## Immediate Next Build Sequence

1. Add missing DDL and an initialization helper for all MVP gold tables.
2. Add small fixture datasets and tests for a full local build path.
3. Implement local file-based property listing ingestion.
4. Implement subway stop ingestion and pass configured POI categories into Google Maps ingestion.
5. Add persisted property context pipeline that reads DuckDB inputs and writes `gold.fct_property_context`.
6. Upgrade the Streamlit app to read `fct_property_context`, show score breakdowns, and support property selection.
7. Document source acquisition and decide the real property listing source after the fixture-backed MVP works.
