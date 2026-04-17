# NYC Property Finder  
### Data Product & Application Spec (V1)

## 1. Objective

Build a **map-based application** that helps identify and evaluate properties in NYC by combining:

- Neighborhood data (demographics, safety, housing)
- Mobility (subway access)
- Personal lifestyle data (Google Maps saved places)
- Property listings (StreetEasy, RentHop, etc.)

The product focuses on **contextual discovery**, not just filtering listings.

---

## 2. Core User Problems

Users struggle to:
- Understand neighborhood differences beyond price
- Evaluate lifestyle fit (proximity to places they care about)
- Compare properties across neighborhoods
- Identify undervalued or high-fit areas

---

## 3. MVP Scope

### Geography
- NYC (start with 1–2 boroughs: Brooklyn + Manhattan)

### Included
- NTA boundaries (primary UX layer)
- Tract-level feature computation
- Subway stops + lines
- Google Maps saved places (user-specific POIs)
- Property listings (1–2 sources)
- Property scoring (simple)

### Excluded (V2+)
- Advanced ML pricing models
- Full city coverage
- Real-time pipelines
- School quality, 311, flood risk

---

## 4. System Architecture

### Medallion Structure

#### Bronze
Raw ingestion:
- ACS / Census
- NYC Open Data
- Subway (GTFS)
- Google Maps exports
- Property listings (scraped)

#### Silver
Cleaned + standardized:
- tract_features_raw
- nta_features_raw
- poi_clean
- property_listings_clean

#### Gold
Analytics-ready:
- fct_tract_features
- fct_nta_features
- dim_user_poi
- dim_property_listing
- fct_property_context

---

## 5. Data Model

### Geography

#### dim_tract
- tract_id
- geometry
- nta_id

#### dim_nta
- nta_id
- name
- geometry

---

### Neighborhood Features

#### fct_tract_features
- tract_id
- median_income
- median_rent
- median_home_value
- pct_bachelors_plus
- median_age
- crime_rate_proxy

#### fct_nta_features
- nta_id
- aggregated metrics from tract

---

### POI Layer

#### dim_user_poi
- poi_id
- name
- category
- source_list_name
- lat
- lon

---

### Property Listings

#### dim_property_listing
- property_id
- source
- source_listing_id
- address
- lat
- lon
- price
- beds
- baths
- listing_type
- url
- ingest_timestamp

---

### Property Context

#### fct_property_context
- property_id
- tract_id
- nta_id
- nearest_subway_stop
- subway_lines_count
- poi_count_10min
- poi_category_counts
- neighborhood_score
- mobility_score
- personal_fit_score
- property_fit_score

---

## 6. Core Pipelines

### Tract → NTA Mapping
- Spatial join using centroid
- Assign tract to NTA

### POI Ingestion
- Export Google Maps data
- Parse and categorize
- Load into dim_user_poi

### Property Ingestion
- Scrape StreetEasy / RentHop
- Normalize schema
- Deduplicate

### Property Context Enrichment
- Join property → tract → NTA
- Compute distances and scores

---

## 7. Scoring

Property Fit Score =
0.4 * Neighborhood +
0.25 * Mobility +
0.35 * Personal Fit

---

## 8. Application Design

### Map Explorer
- Layers: Neighborhood, Transit, POIs, Properties

### Neighborhood Panel
- Metrics and trends

### Property Detail
- Listing + scores + nearby context

### Shortlist
- Saved and compared properties

---

## 9. MVP Success Criteria

- Visual neighborhood exploration
- Personal POIs visible
- Listings enriched with context
- Ability to identify high-fit properties
