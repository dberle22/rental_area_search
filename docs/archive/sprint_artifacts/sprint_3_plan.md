# Sprint 3 Property Context And Scoring Plan

Sprint 3 goal: build `property_explorer_gold.fct_property_context` as the first
app-ready context layer for Property Explorer. The output should give Sprint 4 a
single primary table for map markers, listing cards, filters, and detail panels,
while keeping every score component transparent and honest about missing data.

## Scope

Sprint 3 is an MVP context-and-scoring sprint, not a source expansion sprint.
It should use the Sprint 2 foundation tables already built under
`property_explorer_gold`:

| Table | Current Count | Sprint 3 Use |
| --- | ---: | --- |
| `dim_property_listing` | 22 | Property grain, listing facts, coordinates, active status. |
| `dim_user_poi` | 206 | Nearby personal POI counts, category counts, personal fit score. |
| `dim_tract_to_nta` | 2,327 | Tract-to-NTA labels after property point assignment. |
| `dim_subway_stop` | 496 | Nearest subway stop and straight-line subway distance. |
| `fct_tract_features` | 1,115 | Neighborhood feature join; metric values may be null. |
| `fct_nta_features` | 108 | NTA-level neighborhood fallback/detail context; metric values may be null. |

The sprint should assign each property to tract and NTA where possible, compute
nearest subway context, compute nearby personal POI context, and persist score
components:

- `neighborhood_score`
- `mobility_score`
- `personal_fit_score`
- `property_fit_score`

Neighborhood metric values are currently null in the inspected Metro Deep Dive
NYC tract source. Sprint 3 must make that degradation visible: missing
neighborhood inputs should produce null or explicitly degraded neighborhood
score behavior and a clear data-quality flag or note, not a precise-looking
score.

## Deliverables

- `property_explorer_gold.fct_property_context` populated end to end from the
  Sprint 2 foundation tables.
- A documented build command or runbook addition for rebuilding the context
  table after foundation refreshes.
- Property-to-tract and property-to-NTA assignment using NYC tract geometry plus
  `dim_tract_to_nta`.
- Nearest subway stop name, straight-line distance in miles, and subway line
  count for each property where transit data is available.
- Nearby personal POI count and category-count JSON for each property.
- Transparent scoring components and total/property fit score, with scoring
  weights traceable to `config/scoring_weights.yaml`.
- Missing-data behavior documented in code comments/tests and docs, especially
  for null neighborhood metrics and absent POI data.
- Focused test coverage for geography assignment, transit context, POI context,
  score formulas, null handling, and persisted output shape.
- Data quality checks that can be run before Sprint 4 starts.

## Acceptance Criteria

- `.venv/bin/pytest` passes.
- The context build runs against the current local DuckDB database and writes
  one row per `property_explorer_gold.dim_property_listing.property_id`.
- Every active geocoded property receives `tract_id` and `nta_id` when its point
  falls inside the loaded NYC tract geometries; any misses are counted and
  explained.
- Every property receives nearest subway fields when subway stops are available:
  `nearest_subway_stop`, `nearest_subway_distance_miles`, and
  `subway_lines_count`.
- Every property receives POI context fields: nearby POI count and
  `poi_category_counts` JSON. Empty POI results should be represented as zero
  counts and `{}` when POI data exists but no POIs are nearby.
- `personal_fit_score` uses the loaded Google Maps saved-list POIs. If the POI
  table is absent or empty, `personal_fit_score` is null rather than zero.
- `neighborhood_score` does not pretend precision when tract/NTA metrics are
  missing. With the current null Metro Deep Dive metrics, the output should
  either set `neighborhood_score` to null or expose a clearly degraded fallback
  status that Sprint 4 can display.
- `property_fit_score` combines only available component scores according to a
  documented rule. If a component is null, the total should either be null or
  reweighted with an explicit missing-component flag; silent zero-fill is not
  acceptable for neighborhood metrics.
- Score fields are on a consistent `0-100` scale when non-null.
- The persisted context table is app-ready for Sprint 4 list, map, filter, and
  detail work without requiring Sprint 4 to repeat spatial joins.

## Detailed To-Dos

- [x] Confirm the final `fct_property_context` output columns before code
  changes. Keep existing columns for compatibility, but add app-critical fields
  such as `nta_name` and a clearer nearby POI field if the DDL is updated.
- [x] Add or confirm tract geometry input path in config/runbook. Use NYC
  DCP/ArcGIS 2020 census tract boundaries aligned to the `hm78-6dwm`
  equivalency.
- [x] Implement the context build command path so it can load foundation tables
  from DuckDB and tract polygons from the configured geometry file.
- [x] Spatially assign listing points to tract polygons in EPSG:4326 after
  validating coordinate bounds and CRS.
- [x] Join assigned `tract_id` to `dim_tract_to_nta` to attach `nta_id` and
  `nta_name`.
- [x] Produce a QA summary for unassigned properties, including property ID,
  address, lat/lon, and likely reason.
- [x] Compute nearest subway stop with straight-line distance in miles.
- [x] Count served subway lines from the nearest stop's `lines` field. Normalize
  delimiters so values like `A C`, `A,C`, or `A/C` are counted consistently.
- [x] Compute nearby personal POIs using the MVP straight-line radius. Use
  `0.5` miles unless the product decision changes before implementation.
- [x] Persist POI category counts as JSON object text keyed by normalized
  category.
- [x] Join tract features and, where useful, NTA features. Treat null metric
  rows as missing source coverage, not as zero-valued neighborhoods.
- [x] Revise scoring functions so missing metrics propagate clearly. Avoid
  defaulting null income, education, or rent metrics to zero in a way that looks
  like a real neighborhood score.
- [x] Keep `crime_rate_proxy` out of Sprint 3 scoring and app-ready output
  interpretation.
- [x] Compute `mobility_score` from subway distance and line count.
- [x] Compute `personal_fit_score` from nearby POI count and category diversity
  when POI data is present.
- [x] Compute `property_fit_score` from available components with documented
  weights and missing-component behavior.
- [x] Write the final DataFrame into
  `property_explorer_gold.fct_property_context` with deterministic column order.
- [x] Update the Sprint 2 runbook or create a Sprint 3 runbook section with the
  exact command sequence.
- [x] Add tests and data-quality checks listed below.

## Foundation Table Dependencies

Sprint 3 should depend only on the columns below unless a schema update is
explicitly made.

### `property_explorer_gold.dim_property_listing`

- `property_id`
- `source`
- `source_listing_id`
- `address`
- `lat`
- `lon`
- `price`
- `beds`
- `baths`
- `listing_type`
- `active`
- `url`
- `ingest_timestamp`

### `property_explorer_gold.dim_tract_to_nta`

- `tract_id`
- `nta_id`
- `nta_name`
- `borough`
- `cdta_id`
- `cdta_name`
- `geometry_wkt` only for QA/debug; geometry files remain the preferred polygon
  source for spatial joins.

### `property_explorer_gold.dim_subway_stop`

- `subway_stop_id`
- `stop_name`
- `lines`
- `lat`
- `lon`

### `property_explorer_gold.dim_user_poi`

- `poi_id`
- `name`
- `category`
- `source_list_name`
- `lat`
- `lon`

### `property_explorer_gold.fct_tract_features`

- `tract_id`
- `median_income`
- `median_rent`
- `median_home_value`
- `pct_bachelors_plus`
- `median_age`
- `crime_rate_proxy` only as a nullable legacy/deferred field; do not score it
  for MVP.

### `property_explorer_gold.fct_nta_features`

- `nta_id`
- `nta_name`
- `median_income`
- `median_rent`
- `median_home_value`
- `pct_bachelors_plus`
- `median_age`
- `crime_rate_proxy` only as a nullable legacy/deferred field; do not score it
  for MVP.

## Dependencies And Open Inputs

- Tract geometry file path for NYC 2020 census tracts. Sprint 2 selected
  `hm78-6dwm` for equivalency, but Sprint 3 still needs the polygon file path
  in config or a documented runbook input.
- Confirmation of the MVP nearby POI radius. Default: `0.5` straight-line miles.
- Decision on null-score behavior: prefer `neighborhood_score = null` when all
  neighborhood metrics are missing, and compute `property_fit_score` from the
  available components only when an explicit missing-component flag is present.
- Decision on whether to alter DDL in Sprint 3 to add `nta_name`,
  `poi_count_nearby`, and optional data-quality/status fields. These are useful
  for Sprint 4 but can also be derived if DDL changes are deferred.
- Optional better NYC tract feature source. Not required for Sprint 3, but
  needed if the MVP should show meaningful neighborhood metric values.

Implemented Sprint 3 choices:

- DDL now includes `nta_name`, `poi_data_available`, `poi_count_nearby`,
  `neighborhood_score_status`, `personal_fit_score_status`, and
  `property_fit_score_status`.
- `poi_count_10min` remains for compatibility and mirrors `poi_count_nearby`.
- `neighborhood_score` is null when all neighborhood metrics are missing.
- `property_fit_score` reweights across available components and exposes the
  missing-component behavior through `property_fit_score_status`.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Tract geometry IDs do not match `dim_tract_to_nta.tract_id`. | Add a fixture and live QA check for tract ID format, coverage, and join rate before scoring. |
| Properties near boundaries fail tract assignment. | Report unassigned rows; use exact point-in-polygon first and only add a nearest-tract fallback if misses are real and reviewed. |
| Current Metro Deep Dive metrics are null, making neighborhood scoring weak. | Propagate null/degraded score status and let Sprint 4 display "neighborhood metrics unavailable" rather than a false score. |
| `poi_count_10min` label implies walking time even though the MVP uses straight-line distance. | Document it as a legacy proxy or add `poi_count_nearby` while keeping the old field for compatibility. |
| Subway line counts are wrong because GTFS line strings have inconsistent delimiters. | Normalize line delimiters and add tests with common delimiter variants. |
| Total score becomes misleading when one component is missing. | Add explicit missing-component handling and tests for all-null neighborhood and empty-POI cases. |
| Context table grows into UI-specific denormalization too early. | Carry only fields needed for Sprint 4 map/list/detail and keep source-of-truth dimensions intact. |

## Deferred To Sprint 4

- Map, list, filter, and detail UI that consumes `fct_property_context`.
- Display copy and visual treatment for missing neighborhood metrics.
- Persisted shortlist interactions and comparison view.
- App-level filters for POI categories and score thresholds.
- User-facing explanation panels for scoring methodology.

## Deferred Post-MVP

- Google Places API place resolution.
- Walking-time, routing, or transit-network travel-time calculations.
- Advanced ML or learned recommendations.
- Production scraping, automated listing refresh, and listing history snapshots.
- Crime/safety scoring or safety-themed ranking.
- Weighted/area-population NTA feature aggregation beyond the MVP source
  fallback.
- Manual POI category override UI.

## Test Coverage Needed

- Unit tests for property point-to-tract assignment, including assigned and
  unassigned points.
- Unit tests for tract-to-NTA enrichment and `nta_name` propagation.
- Unit tests for nearest subway distance and nearest stop selection.
- Unit tests for subway line-count parsing across delimiter variants.
- Unit tests for POI counts and category-count JSON within and outside the
  configured radius.
- Unit tests for personal fit when POI data is present, nearby count is zero,
  and POI table is absent.
- Unit tests for neighborhood score behavior when metrics are populated,
  partially missing, and all null.
- Unit tests for total score behavior with all components present and with a
  missing neighborhood component.
- Integration test that builds and writes `fct_property_context` from small
  fixture foundation tables and a tract GeoJSON.
- Schema test confirming the persisted table has the expected columns and one
  row per input property.

## Data Quality Checks Before Completion

- Foundation row counts match the expected Sprint 2 baseline or any difference
  is explained.
- `dim_property_listing.property_id` is unique and every active listing has
  non-null lat/lon inside the NYC MVP bounding box.
- Context row count equals `dim_property_listing` row count, and active context
  row count equals active listing count.
- `tract_id` assignment rate is reported; target is 100 percent for the current
  22 geocoded listings unless a listing falls outside loaded tract coverage.
- Assigned `tract_id` values join to exactly one `dim_tract_to_nta` row.
- `nta_id` and `nta_name` are non-null for every tract-assigned property.
- `nearest_subway_distance_miles` is non-null and non-negative for every
  property when `dim_subway_stop` is populated.
- Subway distance outliers are reviewed, for example distances over `2` miles
  for Manhattan/Brooklyn sample listings.
- `poi_category_counts` is valid JSON for every row.
- Nearby POI counts equal the sum of category counts for every row.
- Score columns are either null for documented missing-data reasons or between
  `0` and `100`.
- With current null neighborhood feature metrics, a QA query confirms that
  neighborhood scores are null/degraded rather than silently computed from
  zero-filled metrics.
- No Sprint 3 output depends on Google Places API, walking-time routing,
  advanced ML, or production scraping.
