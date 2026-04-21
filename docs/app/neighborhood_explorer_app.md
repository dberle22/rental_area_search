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
neighborhood geography, color either layer by the selected demographic metric,
or hide the demographic colors while retaining NTA boundary hover.

## Run

```bash
PYTHONPATH=src .venv/bin/streamlit run app/streamlit_app_v2.py
```

For table readiness, metric coverage, and source-path QA, use the separate QA
surface:

```bash
PYTHONPATH=src .venv/bin/streamlit run app/neighborhood_qa_app.py
```

## Code

- `app/streamlit_app_v2.py`: Streamlit controls, map rendering, and tabular
  demographic review.
- `app/neighborhood_qa_app.py`: QA surface for table readiness, metric coverage,
  and configured source status.
- `src/nyc_property_finder/app/base_map.py`: reusable data-loading,
  tract/NTA geometry assembly, demographic formatting, color ramp generation,
  and PyDeck layer creation.
- `src/nyc_property_finder/app/neighborhood_qa.py`: reusable QA summaries for
  source paths, DuckDB tables, and metric coverage.
- `tests/test_base_map_app.py`: regression tests for metric formatting,
  missing-value colors, target borough filtering, and metric joins.
- `tests/test_neighborhood_qa.py`: regression tests for QA table summaries,
  metric coverage, and configured source status.

## Data Inputs

The app reads paths from `config/settings.yaml` and `config/data_sources.yaml`.
The census tract source uses `sources.census_tracts.path` and
`sources.census_tracts.id_column`; the current local contract points at
`data/raw/geography/census_tracts.geojson` with `GEOID` as the tract ID.

The helper filters to county GEOIDs `36047` and `36061`, matching the current
Brooklyn and Manhattan feature coverage documented in
`sql/gold/fct_tract_features.md`.

## QA Surface

The explorer handles null demographic metrics explicitly so the map can still
render boundaries without precise-looking demographic color. The dedicated QA
app is where missing data should be reviewed. If the local DuckDB has boundary
tables but metric columns are empty, the QA app will show metric coverage as
`0.0%`. Rebuild
`property_explorer_gold.fct_tract_features` and
`property_explorer_gold.fct_nta_features` from the configured Metro Deep Dive
source to populate the demographic color ramp.
