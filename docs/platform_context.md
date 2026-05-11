# Platform Context — Stoop NYC & Demographic Data Projects

Last updated: 2026-05-10

This document is the shared context file for a Claude project that spans multiple
repos. It covers the full platform ecosystem, how the repos relate, current state
in each, and conventions an agent needs to work effectively across them.

---

## Ecosystem Overview

Three repos form an interconnected demographic and real estate data platform:

| Repo | Role | Stack |
|---|---|---|
| `metro_deep_dive` | Upstream demographic data pipeline. Produces tract-level ACS metrics for any US metro. | R, DuckDB |
| `rental_area_search` | Stoop NYC — neighborhood discovery platform for NYC. Consumes `metro_deep_dive` outputs. | Python 3.12, DuckDB, Streamlit, GeoPandas |
| `retail_opportunity_finder` | Southeast US retail investment opportunity explorer. Also consumes `metro_deep_dive`. | Python 3.12, DuckDB, Streamlit, GeoPandas |

A fourth repo, `metro_deep_dive_chatbot`, provides a conversational interface to
`metro_deep_dive` data; it is less tightly coupled to the other two.

**Data flow**:
```
metro_deep_dive.duckdb  ──export──►  rental_area_search (fct_tract_features, fct_nta_features)
                        ──export──►  retail_opportunity_finder (rof_gold schema)
```

The `metro_deep_dive` DuckDB path is local-only on the developer's machine. It
is configured in each consumer repo's ignored `config/data_sources.yaml`.

---

## Shared Tech Conventions

All three consumer repos follow the same stack and patterns:

- **Database**: DuckDB with a named gold schema (`property_explorer_gold`,
  `rof_gold`). Tables are replace-first unless explicitly user-authored.
- **Geometry**: WGS84. GeoJSON geometry loaded at runtime from `data/raw/geography/`;
  not stored in DuckDB. Spatial joins run in GeoPandas/Shapely; results stored
  as WKT in DuckDB.
- **Frontend**: Streamlit + PyDeck.
- **Pipelines**: Python modules under `src/<package>/pipelines/`. Entry points
  are invoked from repo root with `PYTHONPATH=src`.
- **Config**: `config/settings.yaml` (committed), `config/data_sources.yaml`
  (local-only, gitignored). Templates in `config/data_sources.example.yaml`.
- **Proximity**: straight-line distance for MVP; walking-time proxies are deferred.
- **Linting**: Ruff.
- **Testing**: Pytest.

---

## Repo 1: `metro_deep_dive`

**Path**: `<local-projects-root>/metro_deep_dive`

**Purpose**: Modular R pipeline that ingests ACS Census data and produces a
multi-layer DuckDB with tract-level demographic and housing metrics for US
metros. This is the upstream demographic source for both `rental_area_search`
and `retail_opportunity_finder`.

**Key layers**:
- `foundation.tract_features` — raw tract-level ACS metrics
- `gold.housing_core_wide` — cleaned housing metrics per tract
- `gold.population_demographics` — cleaned population/age/education metrics per tract

**Key outputs consumed by downstream repos**:
- Median income, median rent, median home value, `pct_bachelors_plus`, median age
  — all at tract grain

**Important caveat**: as of 2026-04-17, the local `metro_deep_dive` DuckDB does
not expose NYC tract metric rows. `rental_area_search` currently materializes
Brooklyn/Manhattan tract and NTA feature rows with null metric values as an
explicit MVP fallback, and renders null metrics gracefully in the app rather than
producing false scores.

**Stack**: R, DuckDB. Parameterized by GEOID and year range in `config/project.yml`.

---

## Repo 2: `rental_area_search` (Stoop NYC)

**Path**: `<local-projects-root>/rental_area_search`
**Python package**: `nyc_property_finder` (under `src/`)
**Database**: `data/processed/nyc_property_finder.duckdb`, schema `property_explorer_gold`

### Platform Vision

Stoop NYC is a neighborhood intelligence platform for New York City. The name
reflects that a stoop is where NYC neighborhood life happens — local, intimate,
particular. The platform earns its value from a curation layer on top of public
data: personal Google Maps lists, editorial article scrapes, and crowd
contributions that no generic map product has.

### Five Data Products

| Product | Gold Table(s) | Status |
|---|---|---|
| **Curated Places** — personal and editorial place lists | `dim_user_poi_v2` | Active. Google Takeout + 19 article scrapes loaded. Hotels live. Excel upload pending. |
| **City Baseline** — open/official place data (transit, parks, everyday retail, civic) | `dim_public_poi` | Complete. 57,346 rows, 28 categories. Crime and school quality pending. |
| **Neighborhood Context** — ACS tract and NTA metrics | `fct_tract_features`, `fct_nta_features`, `dim_tract_to_nta` | Active. Five-borough geography live. Full NTA metric coverage partial (source: Metro Deep Dive). |
| **Property Listings** — listings enriched with geography, transit, POI context | `dim_property_listing`, `fct_property_context` | Placeholder. 22-row sample only. |
| **Shortlists** — user-authored saves for neighborhoods and properties | `fct_user_shortlist` | Partial. Property shortlist in on-ice Property Explorer V1. Neighborhood shortlist not built. |

### Neighborhood Character Mart

A pre-computed intelligence layer lives in the `neighborhood_character_mart` DuckDB
schema. It is rebuilt by `pipelines/build_neighborhood_character_mart.py`.

Key tables:
- `nta_category_density` — NYC percentile ranking per (NTA × category). Primary
  table for "Top neighborhoods for X" in Stoop Explore.
- `nta_character_profile` — one row per NTA with destination/strong categories,
  top category, and raw livability counts. Primary table for the neighborhood
  character panel.
- `nta_category_controls` — configuration table controlling which categories are
  surfaced in the v1 Explore UI and their evidence thresholds.

Analytics logic: curated POIs and public POIs are spatially joined to NTA
boundaries via GeoPandas (point-in-polygon), then SQL computes per-NTA density
and NYC-relative PERCENT_RANK per category. All mart outputs are pre-computed;
the app reads them directly.

### Two Apps

**Stoop Explore** (`app/stoop_explore.py`)
- Primary question: Where should I spend a day? What is this neighborhood like?
- Audience: NYC residents and suburban day-trippers exploring neighborhoods.
- Core surface: five-borough NTA map, curated POI layer, Explore intelligence
  panel ("Best neighborhoods for X", "What this neighborhood is known for"),
  hotel coverage, public POI overlays.
- Status: active. Sprint 3 surface is built. Sprint 3 launch tasks (UX review,
  smoke test, announcement) remain.
- Entry point: `app/stoop_explore.py`
- Core logic: `src/nyc_property_finder/app/base_map.py`,
  `src/nyc_property_finder/app/stoop_explore.py`

**Stoop Search** (not yet started as a standalone app)
- Primary question (Phase 1): Is this neighborhood somewhere I would like to live?
- Primary question (Phase 2): Does this specific listing work for my life?
- Audience: People evaluating NYC neighborhoods for a move.
- Phase 1 needs: crime, school quality, livability scoring. Buildable after Sprint 1 data work.
- Phase 2 needs: Property Listings data product.

### Key Pipeline Commands

```bash
# Initialize database on a new machine
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.init_database

# Build neighborhood features from Metro Deep Dive
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.build_neighborhood_features

# Rebuild City Baseline (all public POI waves)
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.ingest_public_poi

# Ingest curated POIs from Google Takeout
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.ingest_curated_poi_google_takeout

# Rebuild neighborhood character mart
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.build_neighborhood_character_mart
```

### Curated POI Taxonomy

Taxonomy is driven by `config/poi_categories.yaml`. Three fields form the
canonical taxonomy: `category / subcategory / detail_level_3`.

Three ingestion paths all write to `dim_user_poi_v2`:
1. **Google Takeout** — exported CSV lists from personal Google Maps saved places.
2. **Article Scraping** — publication parsers (Eater, Time Out) and semi-manual
   extractors for editorial sources. Entry: `pipelines/ingest_curated_poi_web_scrape.py`
3. **Excel Upload** — planned; package path reserved at `curated_poi/excel_upload/`.

Canonical grain is one row per physical location (Google Place ID). Raw exports
stay local under `data/raw/google_maps/` and must never be committed.

Current coverage (categories with ≥ 20 NYC-wide curated POIs): restaurants,
bakeries, shopping, hotels, food markets, specialty grocery, bookstores, movie
theaters, record stores. Bars and museums are close to threshold.

### Geography

- Primary neighborhood unit: NTA (Neighborhood Tabulation Area). 262 NTAs cover
  all five boroughs.
- Tract-to-NTA mapping: `dim_tract_to_nta`, built from NYC Open Data equivalency
  table `hm78-6dwm`.
- Geometry files live in `data/raw/geography/` (not committed to git):
  - `census_tracts.geojson`
  - `nta_boundaries.geojson`
  - `tract_to_nta_equivalency.csv`

### Key Decisions

| Decision | Rationale |
|---|---|
| Intelligence outputs pre-computed in DuckDB at pipeline time | Fast app reads, stable contract, reproducible validation. |
| NTA is the primary neighborhood UI language | More legible than census tracts for app users. |
| Rankings use raw POI count as primary sort, not density | Density penalizes large residential NTAs. Stored for future use. |
| Ties broken by subcategory diversity then NTA name | Rewards depth, not just mass, especially for restaurants. |
| Straight-line proximity for MVP | Simpler to implement and explain; walking-time is post-MVP. |
| Crime/safety deferred | Needs stronger source choice and careful product framing. |
| App renders null metrics gracefully | Metro Deep Dive NYC coverage is still partial; never produce false scores. |
| Google Places API used for curated POI resolution | Cache-first; resolved IDs persist locally to minimize API calls. |
| DuckDB file committed to repo for Streamlit Cloud deployment | Sufficient for current scale; MotherDuck is the scale-up path. |

### Current Sprint Status (as of 2026-05-10)

- **Sprint 1** (Data Platform Foundation): Hotels complete. Crime, school quality,
  and crowd upload still open.
- **Sprint 2** (Analysis & Intelligence Design): Explore intelligence spec
  complete. Stoop Search livability scoring design not started.
- **Sprint 3** (Stoop Explore V1 Launch): App surface built. Final UX review,
  smoke test, and public announcement remain.
- Active branch: `stoop-v1`

Full backlog: `docs/planning/current_backlog.md`

---

## Repo 3: `retail_opportunity_finder`

**Path**: `<local-projects-root>/retail_opportunity_finder`
**Database**: `data/processed/rof_app.duckdb`, schema `rof_gold`

**Purpose**: Interactive Streamlit app for exploring retail investment
opportunities across Southeast US markets. Combines census tract demographics,
cluster-based investment zones, and parcel-level data to identify and evaluate
retail sites.

**Architecture**:
```
metro_deep_dive.duckdb  ──export──►  rof_app.duckdb  ──reads──►  Streamlit apps
parcel_geom/fl/*.rds    ──ingest──►  rof_app.duckdb
```

**Three app surfaces**:
1. Zone Explorer — CBSA / tract / zone map with demographic metrics and scoring
2. Retail Parcel Explorer — parcel candidate browser with filters, scoring, and shortlist
3. Data QA App — coverage and data health dashboard

**Cloud deploy subset**: `data/exports/jacksonville_rof.duckdb` (Jacksonville-
scoped subset committed to git for Streamlit Community Cloud).

This repo is structurally similar to `rental_area_search`: same Python/DuckDB/
Streamlit/GeoPandas stack, `src/<package>/` layout, `config/settings.yaml` +
ignored `config/data_sources.yaml`, and a `rof_gold` schema pattern matching
`property_explorer_gold`.

---

## Cross-Repo Dependency Notes

### metro_deep_dive → rental_area_search

- `rental_area_search` reads tract features from the local Metro Deep Dive DuckDB.
- Source path is local-only in `config/data_sources.yaml` (gitignored).
- Fields consumed: `median_income`, `median_rent`, `median_home_value`,
  `pct_bachelors_plus`, `median_age` at tract grain.
- NYC coverage in the local DuckDB is partial as of the last known state.
  `build_neighborhood_features.py` materializes NTA rows with null metrics when
  the source does not cover a tract. The app handles nulls explicitly.

### metro_deep_dive → retail_opportunity_finder

- `retail_opportunity_finder` uses a pipeline step (`export_from_metro.py`) to
  copy a market slice from `metro_deep_dive.duckdb` into `rof_app.duckdb`.
- The R-based Metro Deep Dive pipeline must run first whenever demographic inputs
  need refreshing.

### rental_area_search ↔ retail_opportunity_finder

- No direct data dependency. These are independent consumer apps.
- They share the same developer, stack, and many structural conventions.
- Both use Streamlit Community Cloud for deployment with a committed DuckDB file.

---

## File Conventions Shared Across Repos

| Convention | Rule |
|---|---|
| No absolute paths in committed files | Use repo-relative paths. Never include `/Users/<name>/...` in docs, config, or code. |
| Raw data files are local-only | `data/raw/` and `data/processed/` are gitignored except for committed DB subsets. |
| Config templates committed; actuals gitignored | `config/data_sources.example.yaml` committed; `config/data_sources.yaml` gitignored. |
| Gold tables are replace-first | Unless the table is explicitly user-authored (shortlists). |
| No comments explaining what code does | Only add comments for non-obvious WHY (hidden constraints, subtle invariants). |
| Decision log updated on new decisions | `docs/decision_log.md` in `rental_area_search` is the authoritative record. |

---

## What To Look Up In Each Repo

| Question | Where to look |
|---|---|
| Stoop NYC product strategy and app definitions | `rental_area_search/docs/product_strategy.md` |
| Active sprint tasks and assignments | `rental_area_search/docs/planning/current_backlog.md` |
| DuckDB table contracts and column definitions | `rental_area_search/docs/data_model.md` |
| Pipeline build order and commands | `rental_area_search/docs/pipeline_plan.md` |
| Neighborhood character mart schema and analytics logic | `rental_area_search/docs/data_products/neighborhood_character/neighborhood_character_mart.md` |
| Curated POI taxonomy and ingestion status | `rental_area_search/docs/data_products/curated_places/poi_categories.md` |
| System architecture and pipeline flows | `rental_area_search/docs/architecture.md` |
| Key decisions and rationale | `rental_area_search/docs/decision_log.md` |
| Metro Deep Dive layer structure | `metro_deep_dive/documents/repo_taxonomy.md` |
| Retail Opportunity Finder architecture | `retail_opportunity_finder/PLAN.md` |
