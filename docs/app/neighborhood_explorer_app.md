# Neighborhood Explorer App

## Summary

`app/streamlit_app_v2.py` is the Neighborhood Explorer Streamlit entry point.
It keeps the existing `app/streamlit_app.py` Property Explorer intact and starts
from the shared geography and demographic foundation:

- NYC five-borough census tracts from `data/raw/geography/census_tracts.geojson`.
- Tract-to-neighborhood labels from
  `property_explorer_gold.dim_tract_to_nta`.
- Tract demographic metrics from
  `property_explorer_gold.fct_tract_features`.
- Neighborhood demographic metrics from
  `property_explorer_gold.fct_nta_features`.

The first product surface is a base map that can switch between tract and
neighborhood geography, color either layer by the selected demographic metric,
or hide the demographic colors while retaining NTA boundary hover. The current
default experience starts in neighborhood mode with curated POIs enabled,
public POIs disabled, and `subway_station` as the default public category when
the public layer is turned on.

## Run

```bash
PYTHONPATH=src .venv/bin/streamlit run app/streamlit_app_v2.py
```

For table readiness, metric coverage, POI inventory QA, and source/freshness
checks, use the separate QA surface:

```bash
PYTHONPATH=src .venv/bin/streamlit run app/neighborhood_qa_app.py
```

## Code

- `app/streamlit_app_v2.py`: Streamlit controls, map rendering, and tabular
  demographic review.
- `app/neighborhood_qa_app.py`: QA surface for table readiness, demographic and
  POI coverage, and configured source/freshness status.
- `src/nyc_property_finder/app/base_map.py`: reusable data-loading,
  tract/NTA geometry assembly, demographic formatting, color ramp generation,
  PyDeck layer creation, POI count enrichment, and cached geography loading.
- `src/nyc_property_finder/app/neighborhood_qa.py`: reusable QA summaries for
  source paths, DuckDB tables, demographic coverage, POI inventories, and
  freshness signals.
- `tests/test_base_map_app.py`: regression tests for metric formatting,
  missing-value colors, target borough filtering, and metric joins.
- `tests/test_neighborhood_qa.py`: regression tests for QA table summaries,
  metric coverage, POI inventory coverage, and configured source status.

## Data Inputs

The app reads paths from `config/settings.yaml` and `config/data_sources.yaml`.
The census tract source uses `sources.census_tracts.path` and
`sources.census_tracts.id_column`; the current local contract points at
`data/raw/geography/census_tracts.geojson` with `GEOID` as the tract ID.

The current tract geometry and feature build support all five boroughs. Public
and curated POI points are filtered against the loaded tract geometry at app
load, so records can remain in the underlying tables for future regional
expansion without drawing outside the supported map footprint today.

`fct_nta_features` now follows a stronger neighborhood-native contract and
includes `borough` and `tract_count` alongside the demographic metrics.

## Current UX

- Default geography is `Neighborhoods`
- Curated POIs are on by default
- Public POIs are off by default and lazy-loaded only when toggled on
- Public POI selection starts at `subway_station`
- The table beneath the map shows the core demographic metrics together and
  sorts by the selected metric
- Polygon tooltips include demographic context plus curated/public POI counts
  for quick neighborhood or tract review

## Performance Notes

A timing pass on 2026-04-28 showed that the shared geography load is now the
main backend cost, while metric switches are cheap after the refactor:

- `load_base_geography_data`: about `1.37s`
- `build_base_map_data_from_loaded(...)`: about `0.04s` per metric switch
- `load_poi_map_data`: about `0.07s`
- `load_public_poi_map_data(subway_station)`: about `0.06s`

The remaining perceived delay is more likely dominated by Streamlit rendering
and browser-side map draw cost than by repeated backend data assembly.

## QA Surface

The explorer handles null demographic metrics explicitly so the map can still
render boundaries without precise-looking demographic color. The dedicated QA
app is where missing data should be reviewed. If the local DuckDB has boundary
tables but metric columns are empty, the QA app will show metric coverage as
`0.0%`. Rebuild
`property_explorer_gold.fct_tract_features` and
`property_explorer_gold.fct_nta_features` from the configured Metro Deep Dive
source to populate the demographic color ramp. The QA surface also reports POI
coverage against the full configured curated and public category inventories so
missing categories remain visible instead of silently dropping from the summary.
