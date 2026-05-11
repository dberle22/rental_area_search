# Property Explorer MVP Build Plan

## Current Repo Assessment

The repository is a working Python scaffold for a local NYC property discovery
data product. It already has a `src/` package layout, YAML config, DuckDB
service, geospatial helpers, file-backed ingestion starters, a minimal
Streamlit/PyDeck app, notebooks, docs, SQL DDL, and starter unit tests.

Important current facts:

- Use `.venv/bin/pytest` or activate `.venv`; `pytest` may not be available
  globally.
- `data/raw`, `data/interim`, and `data/processed` are local runtime folders.
  The repo should not assume real source data is checked in.
- Starter DDL exists under the old `gold` schema for the current tables:
  `dim_tract_to_nta`, `dim_subway_stop`, `dim_user_poi`,
  `dim_property_listing`, `fct_tract_features`, `fct_nta_features`, and
  `fct_property_context`. Sprint 2 should migrate these app-facing tables to
  `property_explorer_gold` and add the persisted shortlist contract if still
  missing.
- Starter pipeline modules exist for database initialization, local property
  file ingestion, subway stop ingestion, Google Maps POI ingestion, tract to NTA
  mapping, neighborhood features, and property context scoring.
- Property ingestion is intentionally file-backed for the MVP. StreetEasy and
  RentHop code should be treated as future adapters until source access and
  terms are settled.
- The Streamlit app is still the thinnest layer. It needs stronger listing
  cards, filters, map layers, property detail, neighborhood context, and
  shortlist/comparison behavior.

## MVP Product Definition

The MVP should help a user evaluate NYC property listings by combining listing
facts, neighborhood context, subway access, and personal saved places. The app
should make the answer inspectable: why a property ranks well should be visible
through score components and nearby context, not hidden behind a black-box score.
Google Maps saved places are a key MVP input because they make the product
personal rather than just another listing map.

### MVP User Workflow

This is the product workflow the user should experience after the local database
has been built.

1. Open the Streamlit map explorer.
2. See property listings, NTA/neighborhood context, subway stops, and Google
   Maps personal POIs on the map.
3. Filter listings by property facts such as price, beds, baths, listing type,
   source, and borough or NTA.
4. Filter or sort by contextual facts such as total score, neighborhood score,
   subway access, and nearby Google Maps POI categories.
5. Select a listing and review a property detail view with address, price,
   beds/baths, listing URL, NTA, nearest subway, nearby POIs, neighborhood
   metrics, and score breakdown.
6. Add promising listings to a local shortlist for side-by-side comparison.

### Build Workflow

This is the engineering workflow needed to support the MVP user workflow.

1. Define the data contracts, source paths, and local database architecture.
2. Load foundational datasets into DuckDB: geography, transit, POIs,
   neighborhood features, and property listings.
3. Build enriched property context tables that join listings to geography,
   transit, POIs, and scores.
4. Implement the app views and interactions against those persisted contracts.
5. Make the build reproducible with one documented command or short command
   sequence once the working data path is proven.

### MVP Non-Goals

- Production scraping at scale.
- Real-time listing refresh.
- Advanced ML pricing or recommendation models.
- Full NYC data completeness beyond enough borough coverage for a credible demo.
- Authentication, account management, or cloud deployment. A lightweight
  `user_id` field for local shortlist ownership is still in MVP scope.

## Engineering Principles

- Build the foundational data platform before polishing reproducibility.
- Keep the first end-to-end path file-backed and deterministic before adding
  fragile external acquisition.
- Treat table contracts as product interfaces: document sources, required
  fields, grain, use cases, and app dependencies.
- Prefer source adapters that normalize CSV, GeoJSON, KML, and JSON files before
  website scraping.
- Keep geospatial calculations in GeoPandas/Shapely until scale requires DuckDB
  spatial extensions or spatial indexes.
- Preserve simple, transparent scoring and expose score components in the app.
- Add tests around transforms and pipeline table outputs, not visual polish
  alone.
- Treat notebooks as exploration records; production logic should live under
  `src/nyc_property_finder`.

## Data Models And Architecture

The MVP should use a local medallion-style architecture even if some early
tables are materialized directly into `property_explorer_gold`. The important
part is that each data product has an explicit contract.

### Storage Layers

- `raw`: local source files under `data/raw`, unchanged except for manual
  download/export naming.
- `bronze`: optional first-read tables or artifacts that preserve source shape.
  This can be deferred where a simple file adapter is enough.
- `silver`: normalized, source-specific records with common field names and data
  types.
- `property_explorer_gold`: app-ready dimensions and facts in DuckDB.

### Core Property Explorer Gold Contracts

| Table | Grain | Primary Source | Main Use Cases |
| --- | --- | --- | --- |
| `property_explorer_gold.dim_property_listing` | One current listing per normalized property/listing ID | Local CSV/JSON listing export first; source adapters later | Listing cards, map markers, property filters, detail view |
| `property_explorer_gold.dim_tract_to_nta` | One tract to assigned NTA record | NYC tract and NTA geometries | Property neighborhood assignment, NTA labeling |
| `property_explorer_gold.dim_subway_stop` | One subway stop | MTA/NYC transit stop file | Nearest subway, mobility score, map layer |
| `property_explorer_gold.dim_user_poi` | One saved user place | Google Maps KML/JSON export | Personal fit score, POI map layer, nearby POI summary, demo personalization |
| `property_explorer_gold.fct_tract_features` | One tract feature row | ACS/Census and optional proxy inputs | Neighborhood metrics and score components |
| `property_explorer_gold.fct_nta_features` | One NTA feature row | Aggregated tract features | Neighborhood panel and NTA-level filters |
| `property_explorer_gold.fct_property_context` | One enriched listing row | Property Explorer gold listing, geography, transit, POI, and feature tables | Sorting, score breakdown, selected listing context |
| `property_explorer_gold.fct_user_shortlist` | One saved listing per local user/listing pair | In-app save action | Shortlist, comparison, notes, saved metadata |

### Contract Checklist

Each table should have a short contract before implementation is considered
done:

- Grain and primary key.
- Required columns and allowed nulls.
- Source file or adapter.
- Transform assumptions and units.
- Refresh behavior: replace, append, or slowly changing.
- Downstream app surfaces that depend on it.
- Fixture coverage and validation checks.

### Decisions Already Made

- The MVP supports both rentals and sales. `listing_type` should be a controlled
  CSV field and should drive filtering and map/listing visual treatment.
- The first listing source is a manual CSV. Sprint 1 should define the exact CSV
  contract and identify practical source ideas for creating it.
- CSV fields and listing source ideas should be defined during Sprint 1, not
  finalized in the build plan.
- Listing cards should optimize for affordability and commute/lifestyle fit.
  Neighborhood comparison and investment/value analysis are later concerns.
- First real geography coverage should include Manhattan and Brooklyn.
- NTAs are the main neighborhood language in the UI. Tracts are primarily the
  ACS feature grain and must map cleanly to NTAs.
- `fct_nta_features` should be materialized during the foundation build.
- Crime/safety is deferred until there is a stronger source and framing.
- Shortlists should persist in DuckDB, not only Streamlit session state.
- Shortlists should start as one current row per `user_id` plus `property_id`,
  not as a changelog/event table.
- `dim_property_listing` can retain all ingested listings, with an `active` flag
  so older but relevant listings remain available.
- Google Maps POI integration is a core MVP path and must be represented in
  source contracts, tests, scoring, map layers, and demo data.
- The project product name is Property Explorer. App-facing DuckDB tables should
  live in the `property_explorer_gold` schema, replacing the starter `gold`
  schema naming in docs and Sprint 2 implementation.

## Property Listing Definition

The MVP property listing should be a normalized record that supports search,
map display, scoring, and a useful detail panel. It does not need every field a
listing website shows, but it should include enough to judge a property without
leaving the app immediately.

### Required For MVP

- `property_id`: stable internal ID generated from source, source ID, address,
  and/or coordinates.
- `source`: listing provider or file label.
- `source_listing_id`: source-native listing ID when available.
- `address`: display address.
- `lat`, `lon`: listing coordinates.
- `price`: current asking rent or sale price.
- `beds`, `baths`: numeric bedroom and bathroom counts.
- `listing_type`: controlled value, initially `rental` or `sale`.
- `active`: boolean indicating whether the listing is currently active in the
  manual listing file or source refresh.
- `url`: link back to source listing.
- `ingest_timestamp`: timestamp for when the row entered the local database.

### Strong Next Fields

- `neighborhood_label`: source-provided neighborhood, separate from computed
  NTA.
- `borough`: source-provided borough or derived from geography.
- `unit`: apartment or unit label if available.
- `sqft`: interior square footage when available.
- `available_date`: available or listed date.
- `days_on_market`: useful for stale listing flags.
- `no_fee`: rental-specific boolean.
- `broker_fee`: rental-specific amount or boolean if available.
- `amenities`: JSON text or separate bridge table later.
- `description`: optional text for search/detail display.
- `image_url`: optional first image for listing cards.

### Listing Card MVP

The first listing UI should make affordability and commute/lifestyle fit easy to
scan:

- Primary line: price, beds/baths, and address or short title.
- Secondary line: NTA/neighborhood, nearest subway, and top personal POI signal.
- Badges: listing type, source, commute/mobility score, personal fit score, and
  optionally no-fee or days-on-market.
- Actions: open detail, open source URL, shortlist.

### Listing Ingestion Rules

- File-backed CSV/JSON ingestion is the primary MVP path.
- The first real ingestion format should be a manually maintained CSV with an
  explicit required/optional column contract.
- Rows without coordinates should be rejected or quarantined because map and
  spatial scoring depend on location.
- Duplicate listings should collapse by `property_id`, keeping all known
  listings available through `active` status and preserving the latest/current
  representation for app defaults.
- Source adapters such as StreetEasy and RentHop should normalize into the same
  contract instead of creating app-specific branches.

## Google Maps POI Definition

Google Maps saved places should be treated as a first-class MVP dataset. The
demo should show how personal places change listing evaluation, not just that
listings can be mapped.

### Required For MVP

- `poi_id`: stable internal ID.
- `name`: place name.
- `category`: normalized category from keyword rules or user-provided source
  list.
- `source_list_name`: Google Maps saved list name or export grouping.
- `lat`, `lon`: place coordinates.

### POI Product Uses

- Map layer for saved places.
- Nearby POI counts around each listing.
- Category-level counts for listing detail and filtering.
- Personal fit score component.
- Listing card secondary signal, such as top nearby category or count.

### Resolved MVP Choices

- First Google Maps saved-list inputs are custom Bookstores, Museums, and
  Restaurants lists.
- Category assignment uses taxonomy rules from `config/poi_categories.yaml` for
  MVP. The canonical curated taxonomy lives under `curated_taxonomy`; the
  legacy `keyword_taxonomy_rules` block is only for coarse fallback matching in
  the older Google Maps export path. Manual overrides are post-MVP.
- Nearby POI relevance uses straight-line distance for MVP. Sprint 3 should
  default to a `0.5` mile radius unless the product decision changes.

## Shortlist Definition

The MVP shortlist should be persisted in DuckDB so a local user can keep a
review set between app sessions. It does not require authentication, but it
should be designed so a future user/account model can adopt it.

### Required For MVP

- `shortlist_id`: stable internal ID for the saved listing event or current
  saved listing row.
- `user_id`: local user identifier, initially configured or entered in the app.
- `property_id`: linked listing ID.
- `saved_timestamp`: when the user saved the listing.
- `status`: controlled value such as `active`, `archived`, or `rejected`.
- `notes`: optional user notes.
- `metadata_json`: optional JSON text for lightweight app metadata.

### Sprint 1 Design Questions

- Should listing facts be denormalized into the shortlist for historical review,
  or should the app always join back to the current listing/context tables?
- What is the first `user_id` pattern: a fixed local default, a config value, or
  a small app control?

## Sprint Plan

### Sprint 1: Define Data Contracts, Sources, And Decision Docs

Goal: Align the data model, source files, product decisions, and app needs
before adding more implementation. This sprint should produce decision-ready
documentation and questions for review, not quietly lock major schema choices.

Tasks:

- Expand `docs/data_model.md` into table-by-table contracts using the checklist
  above.
- Create a decision log section in `docs/data_model.md` or a companion doc that
  separates confirmed decisions from open questions.
- Draft the manual property listing CSV contract, including required columns,
  optional columns, allowed `listing_type` values, validation rules, and example
  rows.
- Identify first-pass listing source ideas for manually building the CSV, such
  as saved links, copied listing facts, broker exports, marketplace exports, or
  other legally acceptable user-provided data.
- Define Google Maps POI source expectations, including export format, saved
  list handling, category rules, and demo coverage.
- Define the tract to NTA contract: input tract IDs, NTA IDs/names, geometry
  assumptions, centroid/intersection assignment rule, and QA checks for unmapped
  tracts.
- Define the persisted shortlist contract, including primary key, `user_id`,
  notes, metadata, status values, and one-current-row behavior.
- Decide which fields are needed for the first listing card and detail view
  before implementing the UI.
- Confirm which property_explorer_gold tables are MVP-required versus deferred. Crime/safety
  should be marked deferred.
- Update `config/data_sources.yaml` so every MVP source has a path, expected
  format, and source owner/notes after the contracts are reviewed.
- Document minimum viable sample coverage: Manhattan and Brooklyn geography, a
  small set of representative rental and sale listings, subway stops, and Google
  Maps POIs.

Documentation to produce or update:

- `docs/data_model.md`: full table contracts, grains, keys, columns, null rules,
  and downstream uses.
- `docs/contracts/listing_csv_contract.md`: manual listing CSV schema, examples, source
  ideas, and validation rules.
- `docs/source_inventory.md`: source-by-source notes for geography, ACS,
  transit, Google Maps POIs, listings, and deferred crime/safety.
- `docs/decision_log.md`: confirmed decisions, open decisions, owner, and target
  sprint.

Deliverables:

- Reviewed data contracts for the MVP property_explorer_gold tables.
- A proposed manual listing CSV contract ready for user review.
- A proposed Google Maps POI source/category contract ready for user review.
- A proposed persisted shortlist contract ready for user review.
- Source inventory with paths, expected fields, and source ideas.
- A decision log that makes open product/data choices explicit.

Acceptance criteria:

- Every MVP app surface maps to a table and required columns.
- Every property_explorer_gold table has a known source or is explicitly deferred.
- The listing contract is detailed enough to build affordability and
  commute/lifestyle-focused cards and detail views.
- The Google Maps POI contract is detailed enough to test and demo personal-fit
  scoring.
- The user has reviewed the Sprint 1 docs before schema changes are finalized.

### Sprint 2: Build Foundational Data Tables

Goal: Populate the core local DuckDB foundation tables from file-backed inputs
under the Property Explorer naming convention.

Sprint 2 should produce the first trustworthy local database for Manhattan and
Brooklyn sample exploration. It should treat `data/raw/listings_sample.csv` as
the first real listing input, while preserving the broader manual listing CSV
contract for future files. Because the sample currently has blank coordinates
and uses `rent` instead of `rental`, Sprint 2 must include explicit validation,
normalization, geocoding/cache, and quarantine behavior before any listing is
allowed into map or scoring tables.

#### Sprint 2 Workstreams

1. Schema and naming migration.
   - Rename the app-facing DuckDB schema from starter `gold` to
     `property_explorer_gold`.
   - Update DDL, pipeline defaults, app reads, tests, and docs references that
     are part of the Sprint 2 foundation path.
   - Add `property_explorer_gold.fct_user_shortlist` DDL if it is still missing,
     but leave app write behavior for Sprint 4.
   - Keep Python package/database file renaming separate unless it is cheap and
     low-risk; table schema naming is the Sprint 2 requirement.

2. Listing ingestion and geocoding.
   - Treat `data/raw/listings_sample.csv` as the first real sample source and
     keep `data/raw/property_listings.csv` as the default future production
     manual path unless renamed by decision.
   - Normalize sample values into the contract, including `rent` to `rental`,
     default `source` to `manual_csv` or `streeteasy_saved`, default `active` to
     `true`, and derive `source_listing_id` from source URL when possible.
   - Implement or wire a geocoding cache at
     `data/interim/geocoding/listing_geocodes.csv` for rows missing `lat` and
     `lon`.
   - Use manual/cache matches first, then NYC GeoSearch fallback if enabled.
   - Quarantine rows that cannot be confidently geocoded with address, reason,
     and attempted source.
   - Load only geocoded, contract-valid rows into
     `property_explorer_gold.dim_property_listing`.

3. Geography foundations.
   - Load or download/manual-place tract-to-NTA equivalency and geometry inputs
     for Manhattan and Brooklyn.
   - Build `property_explorer_gold.dim_tract_to_nta` from the tabular
     equivalency first, using centroid assignment only as fallback/QA.
   - Confirm tract IDs match the Metro Deep Dive feature IDs and can support
     property point assignment in Sprint 3.

4. Transit foundations.
   - Pick and load the first subway stop source into
     `property_explorer_gold.dim_subway_stop`.
   - Normalize stop ID, stop name, served lines, latitude, longitude, borough or
     neighborhood label when available.
   - Ensure the source covers all Manhattan and Brooklyn sample listing areas.

5. Google Maps POI foundations.
   - Load Google Maps saved places from KML/JSON export or fixture into
     `property_explorer_gold.dim_user_poi`.
   - Preserve source list names and normalize categories using the current
     keyword category approach.
   - Keep unknown categories as `other` and allow absent POI data to produce
     documented null personal-fit behavior later.

6. Neighborhood feature foundations.
   - Identify the Metro Deep Dive source database tables/views needed for the
     tract feature export.
   - Write the Sprint 2 SQL query/export that builds tract-level metrics for
     income, rent, home value, education, and age.
   - Load the result into `property_explorer_gold.fct_tract_features`.
   - Aggregate tract features through the NTA mapping into
     `property_explorer_gold.fct_nta_features`.

7. Validation, tests, and runbook.
   - Add or update fixture tests for schema creation, listing type coercion,
     coordinate bounds, geocode quarantine behavior, duplicate handling, POI
     parsing/category mapping, tract-to-NTA loading, and NTA aggregation.
   - Add a short runbook command sequence for building the foundation tables
     from a fresh DuckDB database.
   - Record any source-specific decisions or blocked inputs in the decision log.

#### Inputs Needed

| Input | Needed From | Needed By | Notes |
| --- | --- | --- | --- |
| Listing sample CSV | User | Start of Sprint 2 | Present at `data/raw/listings_sample.csv`; needs geocoding and `rent` to `rental` normalization. |
| Geocoding choice | User/Codex | Listing ingestion | Default plan is manual/cache CSV plus NYC GeoSearch fallback. User input needed only if exact provider preference changes. |
| Manual geocode cache review | User | Before listing load acceptance | Required for addresses where automated geocoding is missing, ambiguous, or approximate. |
| Google Maps export | User | POI workstream | KML/JSON saved places export or a small fixture; exact custom list names should be confirmed. |
| Subway stop source | Codex, with user preference if speed vs. durability matters | Transit workstream | MTA GTFS is durable; a simpler station CSV is acceptable for demo speed. |
| Tract/NTA equivalency and geometry files | Codex | Geography workstream | Preferred source is NYC Open Data equivalency plus Manhattan/Brooklyn tract/NTA geometries. |
| Metro Deep Dive DuckDB path | User | Feature workstream | Should live in ignored `config/data_sources.yaml`. |
| Metro Deep Dive feature table/view selection | User/Codex | Feature workstream | Codex can inspect candidates if the local DB path is available. |
| Naming decision | User | Schema workstream | Confirmed direction: Product name is Property Explorer; app-facing schema is `property_explorer_gold`. |

Confirmed Sprint 2 input updates:

- Geocoding will use NYC GeoSearch for missing listing coordinates.
- Subway stops will use the best public source Codex can identify, currently the
  MTA official regular subway static GTFS feed.
- Tract/NTA implementation should pause for source alignment before coding the
  geometry loader.
- The local Metro Deep Dive DuckDB path has been shared in
  `config/data_sources.yaml`; the remaining work is source table/view
  selection.
- The project gold layer should be created as `property_explorer_gold`.

#### Deliverables

- `property_explorer_gold` schema created in a fresh local DuckDB database.
- Foundation tables populated from local files, fixtures, or documented
  quarantines:
  `dim_property_listing`, `dim_subway_stop`, `dim_user_poi`,
  `dim_tract_to_nta`, `fct_tract_features`, and `fct_nta_features`.
- `fct_user_shortlist` DDL available for later app writes.
- `data/interim/geocoding/listing_geocodes.csv` cache and quarantine output
  path documented or implemented.
- Manhattan and Brooklyn geography/transit coverage available for real/demo
  runs.
- A repeatable foundation build command sequence in docs.
- Tests that prove each foundation table can be built independently.

#### Acceptance Criteria

- `.venv/bin/pytest` passes.
- A fresh database build creates the `property_explorer_gold` schema and all
  Sprint 2 foundation tables without relying on pre-existing local state.
- `data/raw/listings_sample.csv` either loads into
  `property_explorer_gold.dim_property_listing` with valid coordinates and
  `listing_type = rental`, or every rejected row appears in a documented
  quarantine file with a clear reason.
- Active listing queries default to `active = true`, and duplicate listings
  collapse deterministically by `property_id`.
- Every loaded listing has a valid NYC latitude/longitude, positive price,
  non-negative beds/baths, source URL, source label, and ingest timestamp.
- `property_explorer_gold.dim_user_poi` can be populated from Google Maps
  fixture/export data with preserved `source_list_name` and normalized
  category.
- `property_explorer_gold.dim_subway_stop` contains stops sufficient to compute
  nearest subway distance for the Manhattan/Brooklyn sample area in Sprint 3.
- `property_explorer_gold.dim_tract_to_nta` covers Manhattan and Brooklyn tracts
  and exposes human-readable NTA names.
- `property_explorer_gold.fct_tract_features` contains the agreed Metro Deep
  Dive-derived fields with documented units and percent scales.
- `property_explorer_gold.fct_nta_features` is materialized from tract features
  during the foundation build.
- Invalid inputs fail with clear validation errors or documented quarantine
  behavior; silent row drops are not acceptable.
- The runbook names every required local input and every output table so the
  build can be repeated after deleting the local DuckDB file.

### Sprint 3: Build Property Context And Scoring

Goal: Produce `property_explorer_gold.fct_property_context` as the first
app-ready enriched listing and transparent scoring layer.

Detailed execution plan: `docs/archive/sprint_artifacts/sprint_3_plan.md`.
Build runbook: `docs/archive/sprint_artifacts/sprint_3_context_runbook.md`.

Sprint 3 should use the completed Sprint 2 foundation tables as inputs:
`dim_property_listing`, `dim_user_poi`, `dim_tract_to_nta`,
`dim_subway_stop`, `fct_tract_features`, and `fct_nta_features`.
It should not add new external data dependencies beyond the tract geometry file
needed for point-in-polygon assignment. Google Places API, walking-time routing,
advanced ML, and production scraping remain out of scope.

The context table should assign each property to a tract and NTA where possible,
compute nearest subway stop and straight-line subway distance, compute nearby
personal POI counts and category counts, and preserve score components:
`neighborhood_score`, `mobility_score`, `personal_fit_score`, and
`property_fit_score`.

Because Sprint 2 materialized tract/NTA feature rows with null metric values as
an explicit MVP fallback, Sprint 3 must handle missing neighborhood metrics
honestly. Null neighborhood inputs should produce null or clearly degraded
neighborhood score behavior, not a precise-looking score from zero-filled
metrics.

#### Sprint 3 Workstreams

1. Context schema and contract finalization.
   - Confirm the exact persisted columns in
     `property_explorer_gold.fct_property_context`.
   - Keep current compatibility fields such as `poi_count_10min`; Sprint 3
     retains it as a straight-line proximity proxy.
   - Add app-critical fields such as `nta_name`, `poi_count_nearby`, and score
     status fields before Sprint 4.

2. Geography assignment.
   - Configure or document the NYC 2020 tract geometry file path.
   - Assign listing points to tract polygons.
   - Join assigned tracts through `dim_tract_to_nta` to attach `nta_id` and
     `nta_name`.
   - Produce QA output for unassigned properties.

3. Transit context.
   - Compute nearest subway stop from `dim_subway_stop`.
   - Persist nearest stop display name, straight-line distance in miles, and
     served line count.
   - Normalize subway line delimiters before counting lines.

4. Personal POI context.
   - Count nearby personal POIs using the MVP straight-line radius, defaulting
     to `0.5` miles unless the product decision changes.
   - Persist total nearby POI count and category-count JSON.
   - Keep absent POI table behavior distinct from "POIs loaded but none nearby."

5. Transparent scoring.
   - Use `config/scoring_weights.yaml` as the initial weighting source.
   - Compute `mobility_score` from subway distance and line count.
   - Compute `personal_fit_score` from nearby POI count and category diversity
     when POI data is present.
   - Compute `neighborhood_score` only when enough neighborhood metrics are
     available, or expose a clear null/degraded status.
   - Compute `property_fit_score` from available components using a documented
     missing-component rule.
   - Keep `crime_rate_proxy` out of MVP scoring.

6. Persistence, tests, and QA.
   - Write one context row per property listing with deterministic column order.
   - Add fixture and integration tests for spatial assignment, nearest subway,
     POI counts, scoring formulas, null behavior, and persisted table shape.
   - Add data quality checks for row counts, assignment rates, distance
     outliers, JSON validity, and score ranges.

Deliverables:

- `property_explorer_gold.fct_property_context` populated end to end from the
  Sprint 2 foundation tables.
- Property-to-tract and property-to-NTA assignment where geometry coverage
  allows.
- Nearest subway context for each property where subway data is available.
- Nearby personal POI counts and category counts for each property.
- Transparent score components and total/property fit score.
- Documented missing-data behavior for null neighborhood metrics and absent POI
  data.
- A build command/runbook update and data quality checklist.
- Tests for missing data, spatial assignment, Google Maps POI contribution,
  transit context, and score formulas.

Acceptance criteria:

- `.venv/bin/pytest` passes.
- The context build writes one row per `dim_property_listing.property_id`.
- Every geocoded property receives tract/NTA context where source coverage
  allows, and misses are counted and explained.
- Every property receives nearest subway fields when subway stops are available.
- Every property receives nearby POI context fields. Loaded-but-not-nearby POIs
  produce zero counts and `{}` category counts.
- Personal fit score uses Google Maps saved-list POI data when available and is
  null when the POI table is absent or empty.
- Missing neighborhood metrics degrade clearly. With the current null Metro Deep
  Dive metrics, neighborhood scores should be null or explicitly marked as
  degraded rather than computed as if zero-valued metrics were real.
- Non-null score fields are on a consistent `0-100` scale.
- The app can read `fct_property_context` as the primary table for Sprint 4
  listing sort/filter/detail needs.

### Sprint 4: Implement Listing UI And Map Explorer

Goal: Turn the completed local database into a useful Property Explorer
property review interface.

Detailed execution plan: `docs/archive/sprint_artifacts/sprint_4_plan.md`.

Sprint 4 should make `property_explorer_gold.fct_property_context` the primary
app table for map markers, listing cards, filters, sorting, selected property
detail, and transparent score display. It should keep
`property_explorer_gold.dim_user_poi` and
`property_explorer_gold.dim_subway_stop` as optional context layers, and should
join `property_explorer_gold.fct_user_shortlist` for local saved-listing state.

The first screen should be the actual app experience: filters, map, listing
cards, and selected property detail. No marketing landing page is needed.
Because the current Metro Deep Dive NYC tract metrics are null, the app must
show neighborhood metrics as unavailable and must explain that total/property
fit scores are reweighted across available components.

#### Sprint 4 Workstreams

1. App data access and availability checks.
   - Read active listings from
     `property_explorer_gold.fct_property_context`.
   - Load POI, subway, NTA feature, and shortlist tables only as optional
     enrichments.
   - Add graceful setup states for missing database files, missing tables, and
     empty data.

2. Map and context layers.
   - Display filtered property markers from the context table.
   - Add toggles for Google Maps personal POIs and subway stop layers.
   - Use distinct marker styling and useful tooltips for properties, POIs, and
     subway stops.

3. Listing cards, filters, and sorting.
   - Add cards with price, beds/baths, listing type, address, NTA, nearest
     subway, source, score badges, and status labels.
   - Add filters for listing type, source, price, beds, baths, NTA,
     straight-line subway distance, score thresholds, and POI category presence.
   - Add sorts for overall fit, personal fit, mobility, nearest subway, price,
     beds, and neighborhood/price.

4. Selected property detail.
   - Add selected property state and a detail panel.
   - Show listing facts, source link, NTA/tract context, nearest subway context,
     POI category summary, score breakdown, and NTA feature metrics when
     available.
   - Display null neighborhood metrics and reweighted score status honestly.

5. Shortlist behavior.
   - Phase 1: read and join shortlist rows for the local configured user.
   - Phase 2: implement save/archive/reject and notes writes if low-risk after
     the core read-only app is stable.
   - Defer comparison view and multi-user management.

6. Tests and app QA.
   - Add helper tests for filtering, sorting, POI category JSON parsing, score
     status display, empty table behavior, and shortlist writes if implemented.
   - Smoke-test the app against the current 22-row database and against missing
     optional tables.

Deliverables:

- A Property Explorer Streamlit app whose first screen is the usable
  map/list/detail explorer.
- Primary reads from `property_explorer_gold.fct_property_context`.
- Toggleable personal POI and subway map layers.
- Filtered/sorted listing cards and selected property detail.
- Transparent score breakdowns and missing-data statuses.
- Persisted shortlist behavior if the write path remains small and stable; at
  minimum, a read/join path plus documented remaining write work.
- Focused app helper tests and manual QA checks.

Acceptance criteria:

- `streamlit run app/streamlit_app.py` opens an app that works against
  `data/processed/nyc_property_finder.duckdb`.
- All 22 active context rows appear before filters.
- Filtering and sorting update the map, listing cards, and selected detail.
- Google Maps POIs and subway stops can be shown or hidden as context layers.
- The selected property detail exposes listing facts, source URL, nearest
  subway, nearby POI summary, score breakdown, and missing-data status.
- Null neighborhood metrics are not displayed as zero or precise scores.
- Reweighted total/property scores are labeled clearly.
- Shortlist writes persist across Streamlit refresh if implemented.
- `.venv/bin/pytest` passes.

### Sprint 5: Make The Working Build Reproducible

Goal: Once the data path works, make it easy to rebuild without guessing.

Next workstream planning: `docs/planning/next_workstreams_plan.md`.

Tasks:

- Add or refine a command that initializes schemas and runs the MVP build
  sequence from config.
- Document canonical local commands in README.
- Add a smoke test for a fixture-backed full local build.
- Add acquisition notes or scripts for NYC geography, subway stops, ACS-derived
  features, and listing files.
- Add linting/formatting or CI only after the repo workflow is settled.

Deliverables:

- One command or short documented sequence for rebuilding DuckDB.
- Source acquisition documentation.
- Fixture-backed smoke test for the full local build.

Acceptance criteria:

- A new developer can reproduce the MVP database and app from documented inputs.
- Fragile or legally sensitive scraping work is isolated behind adapters and is
  not required for demo success.

## Open Decisions For Next Review

- Geometry storage: Keep WKT in DuckDB for portability, add GeoParquet sidecars,
  or use DuckDB spatial extension once the data path stabilizes?
- Sprint 4 shortlist write scope: Should the first app implement
  save/archive/reject plus notes, or save/archive only?
- Sprint 4 default listing view: Should rentals and sales both be visible by
  default, or should rentals be the default first view?
- Sprint 4 neighborhood panel: Should unavailable NTA metrics be shown as an
  explicit disabled/unavailable section, or hidden until a non-null source
  exists?
- Listing history depth: Does `active` plus latest row cover v1, or do we need a
  separate listing snapshot table later?

## Risks And Mitigations

- Property scraping risk: website terms, anti-bot behavior, and schema churn can
  stall the MVP. Mitigate by making file-based listing ingestion the primary MVP
  path.
- Source schema drift: NYC, MTA, Census, and listing fields may differ from
  config assumptions. Mitigate with source-specific mapping config and fixture
  tests.
- Mixed rental/sale comparison: affordability differs by listing type. Mitigate
  by filtering/color-coding `listing_type` and avoiding direct rental-versus-sale
  value claims in early scores.
- Score credibility: simple scores can look more precise than they are.
  Mitigate by showing component scores and documenting formula assumptions.
- Empty-data app experience: the app will hide most value without populated
  tables. Mitigate with table checks, fixtures, and setup states.
- Geospatial performance: all-pairs distance helpers are fine for small MVP data
  but may not scale. Mitigate later with spatial indexes, bounding boxes, or
  DuckDB spatial.
- Data privacy: Google Maps saved places may be sensitive. Mitigate by keeping
  user POI files local and excluding raw exports from version control.
- Personalization demo risk: without enough Google Maps POIs, the MVP can look
  generic. Mitigate by making POI fixture/demo coverage part of Sprint 1 and
  Sprint 2 acceptance criteria.

## Immediate Next Build Sequence

1. Implement the Sprint 4 app data access path against
   `property_explorer_gold.fct_property_context`.
2. Build listing filters, sort controls, map layers, and listing cards.
3. Add selected property detail with score breakdown and missing-data statuses.
4. Add shortlist read/join behavior for the configured local user.
5. Implement shortlist writes if the core map/list/detail workflow is stable.
6. Add app helper tests and run `.venv/bin/pytest`.
7. Smoke-test `streamlit run app/streamlit_app.py` against the current 22-row
   database.
