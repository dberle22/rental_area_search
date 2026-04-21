# Sprint 2 To-Dos

Sprint 2 goal: build the first trustworthy Property Explorer foundation database
under the `property_explorer_gold` DuckDB schema.

## Active Decisions

- Project app-facing schema: `property_explorer_gold`.
- Listing sample input: `data/raw/listings_sample.csv`.
- Listing geocoding: NYC GeoSearch, because the sample currently lacks
  latitude/longitude.
- Google Maps saved-list CSVs: resolve place names through NYC GeoSearch for
  MVP and quarantine misses; Google Places API is Post-MVP.
- Subway stop source: MTA official static subway GTFS, with the current regular
  subway feed at `https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip`.
- Tract/NTA tabular source: NYC Open Data 2020 Census Tracts to 2020 NTAs and
  CDTAs Equivalency, dataset `hm78-6dwm`.
- Tract/NTA geometry files: NYC DCP/ArcGIS 2020 Census Tracts and NTA boundary
  files for geometry when Sprint 3 needs polygons/property spatial joins.
- Metro Deep Dive source: local DuckDB path in ignored
  `config/data_sources.yaml`.

## Implementation Checklist

- [x] Record Sprint 2 user decisions in docs.
- [x] Create `property_explorer_gold` schema in DDL.
- [x] Add `property_explorer_gold.fct_user_shortlist` DDL.
- [x] Switch foundation pipeline defaults from `gold` to
  `property_explorer_gold`.
- [x] Switch app/test reads from `gold` to `property_explorer_gold`.
- [x] Normalize listing type aliases such as `rent` to `rental`.
- [x] Add geocoding cache/quarantine module for NYC GeoSearch results.
- [x] Add listing sample ingestion path that geocodes missing coordinates before
  loading.
- [x] Confirm Google Maps POI ingestion mode and required credentials/exports.
- [x] Parse Google Maps saved-list CSV exports.
- [x] Resolve Google Maps CSV POIs with NYC GeoSearch cache/quarantine.
- [x] Align tract/NTA equivalency plus geometry file choices before loader work.
- [x] Add MTA GTFS subway stop downloader/normalizer or documented manual
  download path.
- [x] Inspect Metro Deep Dive DuckDB tables/views for tract feature export.
- [x] Build `property_explorer_gold.fct_nta_features` from tract features and
  tract/NTA mapping.
- [x] Add foundation build runbook command sequence.
- [x] Run full `.venv/bin/pytest`.

## Current Foundation Build Status

- Local DuckDB initialized at `data/processed/nyc_property_finder.duckdb`.
- `property_explorer_gold.dim_property_listing` loaded from
  `data/raw/listings_sample.csv`.
- Loaded listing count: 22 active listings, currently 19 rentals and 3 sales.
- Geocode cache: `data/interim/geocoding/listing_geocodes.csv`.
- Geocode quarantine:
  `data/interim/geocoding/listing_geocode_quarantine.csv`, currently header-only
  after successful matching.
- `property_explorer_gold.dim_user_poi` loaded from Google Maps saved-list CSVs.
- Loaded POI count: 206 geocoded places.
- POI geocode cache: `data/interim/geocoding/poi_geocodes.csv`.
- POI geocode quarantine: `data/interim/geocoding/poi_geocode_quarantine.csv`.
- `property_explorer_gold.dim_tract_to_nta` loaded from NYC Open Data
  `hm78-6dwm`; count: 2,327 tracts.
- `property_explorer_gold.dim_subway_stop` loaded from MTA regular subway GTFS;
  count: 496 stops/stations.
- `property_explorer_gold.fct_tract_features` materialized for Brooklyn and
  Manhattan; count: 1,115 tracts. Metric values are null because the inspected
  Metro Deep Dive source does not currently expose NYC tract metrics.
- `property_explorer_gold.fct_nta_features` materialized for Brooklyn and
  Manhattan; count: 108 NTAs. Metric values are null for the same source-coverage
  reason.

## User Inputs Needed

- Optional POI review: inspect `data/interim/geocoding/poi_geocode_quarantine.csv`
  if more saved places should be manually corrected or retried later.
- Optional feature source follow-up: provide or identify a tract feature source
  with NYC metric coverage if neighborhood scores should use non-null feature
  values before Sprint 3 scoring.
