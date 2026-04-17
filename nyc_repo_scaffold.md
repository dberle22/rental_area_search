# NYC Property Finder
## Repo Scaffold

### Overview
This document defines the repository structure and initial implementation plan.

---

## Repository Structure

```
nyc-property-finder/
├── README.md
├── PROJECT_SPEC.md
├── .gitignore
├── .env.example
├── pyproject.toml
├── requirements.txt
├── config/
│   ├── settings.yaml
│   ├── data_sources.yaml
│   ├── poi_categories.yaml
│   └── scoring_weights.yaml
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── docs/
│   ├── architecture.md
│   ├── data_model.md
│   ├── pipeline_plan.md
│   └── decisions/
├── notebooks/
│   ├── 01_source_audit.ipynb
│   ├── 02_tract_to_nta_mapping.ipynb
│   ├── 03_google_maps_poi_ingestion.ipynb
│   ├── 04_neighborhood_features.ipynb
│   └── 05_property_ingestion.ipynb
├── sql/
│   ├── ddl/
│   ├── bronze/
│   ├── silver/
│   ├── gold/
│   └── marts/
├── src/
│   └── nyc_property_finder/
│       ├── pipelines/
│       ├── scrapers/
│       ├── transforms/
│       ├── services/
│       ├── models/
│       └── utils/
├── app/
│   ├── streamlit_app.py
│   └── pages/
├── tests/
└── output/
```

---

## Key Modules

### Pipelines
```
build_tract_to_nta.py
ingest_google_maps.py
build_neighborhood_features.py
ingest_property_streeteasy.py
ingest_property_renthop.py
build_property_context.py
```

### Scrapers
```
base.py
streeteasy.py
renthop.py
```

### Transforms
```
geography.py
poi.py
listings.py
demographics.py
transit.py
scoring.py
```

---

## Config Files

### poi_categories.yaml
```
categories:
  Restaurants:
  Bars:
  Parks:
  Bookstores:
  Record Stores:
  Museums:
  Coffee Shops:
  Groceries:
  Shopping:
```

### scoring_weights.yaml
```
weights:
  neighborhood: 0.40
  mobility: 0.25
  personal_fit: 0.35
```

### settings.yaml
```
database_path: data/processed/nyc_property_finder.duckdb
target_boroughs:
  - Brooklyn
  - Manhattan
```

---

## Initial Pipelines

### Tract to NTA
- Load tract geometries
- Load NTA boundaries
- Spatial join

### POI Ingestion
- Parse Google Maps export
- Normalize categories

### Neighborhood Features
- Income
- Rent
- Home value
- Education
- Age
- Crime proxy

### Property Ingestion
- StreetEasy scraper
- RentHop scraper

### Property Context
- Join to geography
- Compute scores

---

## Minimal App

Pages:
- Map Explorer
- Neighborhood
- Property
- Shortlist

---

## Next Steps

1. Create repo structure
2. Add config files
3. Implement DuckDB service
4. Build tract to NTA pipeline
5. Build POI ingestion
