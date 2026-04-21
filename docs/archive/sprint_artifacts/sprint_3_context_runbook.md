# Sprint 3 Property Context Build Runbook

This runbook builds the first app-ready Property Explorer context table:
`property_explorer_gold.fct_property_context`.

## Inputs

Required foundation tables from Sprint 2:

- `property_explorer_gold.dim_property_listing`
- `property_explorer_gold.dim_user_poi`
- `property_explorer_gold.dim_tract_to_nta`
- `property_explorer_gold.dim_subway_stop`
- `property_explorer_gold.fct_tract_features`
- `property_explorer_gold.fct_nta_features`

Required local file:

- NYC 2020 census tract geometry, defaulting to
  `data/raw/geography/census_tracts.geojson` from
  `config/data_sources.example.yaml`.

The geometry file must expose the tract ID column configured as
`sources.census_tracts.id_column`; the default is `tract_id`.

## Build Command

After the Sprint 2 foundation tables exist, run:

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.build_property_context
```

To override paths explicitly:

```bash
PYTHONPATH=src .venv/bin/python -m nyc_property_finder.pipelines.build_property_context \
  --database-path data/processed/nyc_property_finder.duckdb \
  --tract-path data/raw/geography/census_tracts.geojson \
  --tract-id-col tract_id
```

The command prints a compact QA summary after writing
`property_explorer_gold.fct_property_context`.

## Sprint 3 Output Fields

Sprint 3 adds app-critical fields to the context table:

- `nta_name`
- `poi_data_available`
- `poi_count_nearby`
- `neighborhood_score_status`
- `personal_fit_score_status`
- `property_fit_score_status`

`poi_count_10min` is retained for compatibility, but it is the same
straight-line nearby count as `poi_count_nearby`, not a walking-time measure.

## Missing-Data Behavior

- Neighborhood score is null when all neighborhood metrics are missing.
- Personal fit score is null when POI data is absent or empty.
- Total/property fit score reweights across available score components.
- `property_fit_score_status` is `reweighted_missing_components` when one or
  more components are missing but at least one component is available.
- `crime_rate_proxy` remains out of MVP scoring.

## QA Queries

```sql
SELECT COUNT(*) AS context_rows
FROM property_explorer_gold.fct_property_context;

SELECT
  COUNT(*) AS rows,
  SUM(CASE WHEN active THEN 1 ELSE 0 END) AS active_rows,
  SUM(CASE WHEN tract_id IS NOT NULL THEN 1 ELSE 0 END) AS tract_assigned_rows,
  SUM(CASE WHEN tract_id IS NOT NULL AND nta_name IS NULL THEN 1 ELSE 0 END) AS missing_nta_name_rows,
  SUM(CASE WHEN nearest_subway_distance_miles > 2 THEN 1 ELSE 0 END) AS subway_distance_over_2_miles_rows
FROM property_explorer_gold.fct_property_context;

SELECT
  neighborhood_score_status,
  personal_fit_score_status,
  property_fit_score_status,
  COUNT(*) AS rows
FROM property_explorer_gold.fct_property_context
GROUP BY 1, 2, 3
ORDER BY rows DESC;

SELECT property_id, address, lat, lon
FROM property_explorer_gold.fct_property_context
WHERE tract_id IS NULL;
```

Before Sprint 4, confirm:

- Context row count equals listing row count.
- Active context row count equals active listing count.
- Tract assignment misses are zero or explained.
- `poi_category_counts` is valid JSON.
- Non-null scores are between `0` and `100`.
- Null neighborhood score behavior matches the current null Metro Deep Dive
  feature fallback.
