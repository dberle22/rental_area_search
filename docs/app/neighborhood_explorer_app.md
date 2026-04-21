# Neighborhood Explorer App

## Summary

`app/streamlit_app_v2.py` is the Neighborhood Explorer Streamlit entry point.
It keeps the existing `app/streamlit_app.py` Property Explorer intact and starts
from the shared geography and demographic foundation:

- Brooklyn and Manhattan census tracts from `data/raw/geography/census_tracts.geojson`.
- Tract-to-neighborhood labels from
  `property_explorer_gold.dim_tract_to_nta`.
- Tract demographic metrics from
  `property_explorer_gold.fct_tract_features`.
- Neighborhood demographic metrics from
  `property_explorer_gold.fct_nta_features`.

The first product surface is a base map that can switch between tract and
neighborhood geography and color either layer by the selected demographic
metric.

## Run

```bash
PYTHONPATH=src .venv/bin/streamlit run app/streamlit_app_v2.py
```

## Code

- `app/streamlit_app_v2.py`: Streamlit controls, map rendering, summary metrics,
  and tabular review.
- `src/nyc_property_finder/app/base_map.py`: reusable data-loading,
  tract/NTA geometry assembly, demographic formatting, color ramp generation,
  and PyDeck layer creation.
- `tests/test_base_map_app.py`: regression tests for metric formatting,
  missing-value colors, target borough filtering, and metric joins.

## Data Inputs

The app reads paths from `config/settings.yaml` and `config/data_sources.yaml`.
The census tract source uses `sources.census_tracts.path` and
`sources.census_tracts.id_column`; the current local contract points at
`data/raw/geography/census_tracts.geojson` with `GEOID` as the tract ID.

The helper filters to county GEOIDs `36047` and `36061`, matching the current
Brooklyn and Manhattan feature coverage documented in
`sql/gold/fct_tract_features.md`.

## Current Data Caveat

The app handles null demographic metrics explicitly. If the local DuckDB has
boundary tables but metric columns are empty, the map still renders tract and
neighborhood boundaries and shows metric coverage as `0.0%`. Rebuild
`property_explorer_gold.fct_tract_features` and
`property_explorer_gold.fct_nta_features` from the configured Metro Deep Dive
source to populate the demographic color ramp.
