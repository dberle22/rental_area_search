# Sprint 1 Acceptance Checklist

Sprint 1 goal: align the data model, source files, product decisions, and app
needs before adding more implementation.

## Complete

- [x] Expand `docs/data_model.md` into table-by-table MVP gold contracts.
- [x] Separate confirmed decisions from open questions in
  `docs/decision_log.md`.
- [x] Draft the manual property listing CSV contract.
- [x] Identify first-pass listing source ideas and choose StreetEasy/Zillow as
  first manual sources.
- [x] Define Google Maps POI source expectations and MVP category behavior.
- [x] Define tract-to-NTA source strategy, preferring an official equivalency
  table before geometry fallback.
- [x] Define the persisted shortlist contract.
- [x] Decide first listing card/detail fields, including `no_fee` for rentals
  and excluding images/days-on-market from MVP.
- [x] Confirm MVP-required versus deferred tables and sources.
- [x] Create a local-only data source config pattern with
  `config/data_sources.example.yaml` tracked and `config/data_sources.yaml`
  ignored.
- [x] Document minimum viable sample coverage.
- [x] Add a Post-MVP improvements doc for deferred ideas.
- [x] Validate current config/docs changes with the existing test suite.

## Confirmed Decisions

- [x] MVP supports rentals and sales, leaning rental for first sample listings.
- [x] Manual CSV/JSON is the first listing source path.
- [x] StreetEasy and Zillow are the first manual listing sources.
- [x] Listing images are post-MVP.
- [x] `no_fee` is required for rental rows in the manual CSV.
- [x] `days_on_market` is deferred until scraper/adapter data exists.
- [x] Approximate listing coordinates are acceptable when marked.
- [x] Address-only rows can be geocoded before gold load/scoring.
- [x] Geocoding starts with a manual/cache CSV plus NYC GeoSearch fallback.
- [x] Manhattan and Brooklyn are the first geography coverage target.
- [x] NTA is the primary neighborhood UI language.
- [x] Google Maps custom Bookstores, Museums, and Restaurants lists are the
  first POI coverage target.
- [x] Keyword POI categories are enough for MVP.
- [x] Straight-line distance is the MVP proximity method.
- [x] Missing POI data leaves `personal_fit_score` null.
- [x] Metro Deep Dive DuckDB-derived features are the first neighborhood feature
  source path.
- [x] Metro Deep Dive feature assembly moves to a Sprint 2 SQL query.
- [x] Shortlists persist in DuckDB.
- [x] Shortlist `user_id` comes from `config/settings.yaml`.
- [x] Listing `active` stays on `dim_property_listing`.
- [x] Full listing snapshot/history is deferred.
- [x] Crime/safety is deferred.

## Sprint 2 Carry-Forward

- [ ] Write a SQL query to assemble tract-level features from the relevant Metro
  Deep Dive tables/views.
- [ ] Identify the exact Metro Deep Dive tables/views needed by that query.
- [ ] Implement DDL updates for `active`, `no_fee`, geocoding metadata, shortlist
  persistence, and any agreed context-field names.
- [ ] Implement tract-to-NTA equivalency ingestion from the NYC Open Data CSV.
- [ ] Implement or stub listing geocoding with cache CSV plus NYC GeoSearch
  fallback.
- [ ] Update ingestion tests to enforce the finalized listing CSV contract.
