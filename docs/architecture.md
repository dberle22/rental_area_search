# Architecture

NYC Property Finder follows a lightweight three part organization: Data Platform, Data Processing, and Frontend Applications.

For table-level contracts, source coverage, and build entrypoints, use
`docs/data_model.md` as the primary reference. `docs/source_inventory.md`
contains the longer source notes: external URLs, local path conventions,
selected MVP sources, and deferred data ideas. `docs/pipeline_plan.md` is the
current operational build runbook.


## Data Platform

The Data Platform follows a lightweight medallion pattern for data processing:

- Bronze: Raw files and API exports (e.g., CSV, GeoJSON, KML from sources like Google Maps or MTA).
- Silver: Cleaned, source-specific tables with basic normalization.
- Gold: Analytics-ready dimensions and facts for app consumption.

DuckDB serves as the local analytical database, with GeoPandas handling spatial operations (e.g., geometry calculations) before storing results as WKT in DuckDB. This architecture supports local, file-backed data for the MVP, prioritizing reproducibility over real-time ingestion.

Data is split into foundational layers (base geography and demographics) and user-facing points (properties and POIs). All data flows through the medallion layers into DuckDB schemas like `property_explorer_gold` for app-ready tables. See `data_model.md` for detailed table contracts, validation rules, source coverage, and build entrypoints.

1. Foundations
    - Tracts
    - Neighborhoods
    - Counties
    - Foundational Points: Subways, Parks, etc. These are points of interest with public entry points such as subways.
2. User-facing Points
    - Properties
        - Rentals
        - Sales
    - Points of Interest
        - Museums
        - Restaurants
        - Bars
        - Shops
        - Etc

### Core Foundational Data
These are the base layers for geography and context, enabling aggregation and filtering across tracts, neighborhoods, and counties.

#### Tracts
Demographic features (e.g., income, population, age from ACS data via Metro Deep Dive) and geometry (from census tract boundaries). Includes crosswalks to neighborhoods and counties for roll-ups.

The main products in this layer are:

- tracts_features - refer to sql/gold/fct_tract_features.sql for reference
- tracts_geom - see data/raw/geography/census_tracts.geojson for tracts
- tracts_counties_xwalk - exists in Metro Deep Dive DuckDB
- tracts_neighborhood_xwalk - see data/raw/geography/tract_to_nta_equivalency.csv

#### Neighborhoods
Aggregated tract data into Neighborhood Tabulation Areas (NTAs) for user-facing summaries (e.g., median rent by area).

Sourced from Tract Crosswalks and NTA boundaries. Built using sql/gold/fct_nta_features.sql for reference.

#### Counties
Borough-level (e.g., Brooklyn, Manhattan) for high-level filtering. Acts as the lowest aggregation level.
Sources: Tract-to-county mappings.
Tables: Crosswalks in tract tables (no dedicated county table yet).
Reference: Tract crosswalks in data/interim/processed/nyc_property_finder.duckdb.

#### Foundational Points
Public infrastructure like subway stops and parks for mobility and context.

Sources: MTA for subways; future open-source points (not yet implemented).
Tables: property_explorer_gold.dim_subway_stop.
Reference: src/nyc_property_finder/pipelines/ingest_subway_stops.py

### POI and Property Layer
These layers add point-based data for exploration, including geocoding from addresses to coordinates.

#### Property
Rental and sale listings with details like price, beds, and availability. Geocoded from addresses; failed geocodes quarantined.
Sources: Manual CSV/JSON (MVP), StreetEasy/RentHop scrapers.
Tables: property_explorer_gold.dim_property_listing, fct_property_context.
Reference: data_model.md for listing contract; scrapers for scraping logic.

#### Points of Interest
User-curated locations (e.g., bars, restaurants, museums) from Google Maps, plus public points (subways, parks).
Sources: Google Maps Takeout or saved-list exports (KML/JSON/CSV), with NYC GeoSearch fallback for saved-list CSVs that only include names and URLs. Google Places API resolution is post-MVP.
Tables: property_explorer_gold.dim_user_poi.
Reference: poi_categories.yaml for categories; ingest_google_maps.py.

## Data Processing
Pipelines ingest raw data into bronze, transform it through silver, and materialize gold tables. Scripts are Python-based under src/nyc_property_finder/pipelines, with notebooks for exploration. MVP focuses on file-backed, deterministic runs. See pipeline_plan.md for build steps.

### Ingestion Scripts
These pull raw data into bronze tables, normalizing formats like CSV or GeoJSON.

Reference: data_sources.yaml for source configs; data/raw for inputs.

#### Subway Stops
Ingests MTA data for transit points.
Script: ingest_subway_stops.py.
Output: Bronze subway table.

#### POI Processing (Google Maps)
Processes user exports for personal locations.
Script: ingest_google_maps.py.
Output: Bronze POI table.

#### Property Data
Handles listings from files or scrapers (StreetEasy, RentHop).
Scripts: ingest_property_file.py, ingest_property_streeteasy.py, ingest_property_renthop.py.
Output: Bronze property table with geocoding.

### Transformations

#### Tract to NTA
Builds geography crosswalks.
Script: build_tract_to_nta.py.
Output: dim_tract_to_nta.

#### Neighborhood Features
Aggregates tract metrics to NTAs.
Script: build_neighborhood_features.py.
Output: fct_nta_features.

#### Property Context
Scores listings with nearby POIs and context.
Script: build_property_context.py.
Output: fct_property_context.
Reference: scoring_weights.yaml for scoring logic.

#### Database Init
Sets up schemas and tables.
Script: init_database.py.

Note: Notebooks (e.g., 02_tract_to_nta_mapping.ipynb) explore logic but production code lives in src. Detailed build order and commands live in pipeline_plan.md.

## Frontend Application
Two Streamlit apps consume gold tables for exploration. Both use PyDeck for maps and DuckDB for queries. See planning/build_plan.md for the broader MVP workflow history.

### Property Search Helper
Interactive app for evaluating listings: map view with filters (price, beds, borough), sorting by scores, property details (nearby POIs, subway), and shortlist for comparison.
Code: app/streamlit_app.py and src/nyc_property_finder/app/explorer.py.
Data: Pulls from dim_property_listing, fct_property_context.

### Neighborhood Explorer
Base map for browsing tracts/NTAs: demographic layers (income, age), borough filters, no properties. This app can render boundaries even when demographic metrics are still null.
Code: app/streamlit_app_v2.py and src/nyc_property_finder/app/base_map.py.
Data: Pulls from fct_tract_features, fct_nta_features.

### Data Flow and Integration
Data starts in raw, flows through pipelines (ingestion → transformation) into nyc_property_finder.duckdb, and feeds apps. Geocoding and scoring happen mid-flow; quarantine files handle errors. For reproducibility, run pipelines in order (e.g., init DB first). Future: CLI orchestration (not yet implemented).
