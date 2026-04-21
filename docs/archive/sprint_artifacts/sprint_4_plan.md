# Sprint 4 Streamlit Map/List/Detail Plan

Sprint 4 goal: turn the local Property Explorer database into the first useful
property review interface. The app should open directly into a usable
map/list/detail workflow backed primarily by
`property_explorer_gold.fct_property_context`, with Google Maps personal POIs
and subway stops available as context layers.

## Scope

Sprint 4 is an app implementation sprint, not a data acquisition sprint. It
should consume the completed Sprint 2 foundation tables and Sprint 3 context
table. It should make the current sample of 22 active listings genuinely
reviewable even though neighborhood metrics are currently unavailable.

In scope:

- Read listing map, list, filter, sort, and detail data primarily from
  `property_explorer_gold.fct_property_context`.
- Display active listings on an interactive map.
- Display Google Maps personal POIs from
  `property_explorer_gold.dim_user_poi` as an optional context layer.
- Display subway stops from `property_explorer_gold.dim_subway_stop` as an
  optional context layer.
- Add scannable listing cards/list view.
- Add practical filters and sorting for the 22-row MVP sample.
- Add selected property detail with listing facts, source link, transit context,
  POI context, score breakdown, and missing-data statuses.
- Implement the smallest useful persisted shortlist path against
  `property_explorer_gold.fct_user_shortlist`, if it remains low-risk.
- Clearly label straight-line distance proxies and unavailable neighborhood
  metrics.

Out of scope:

- Google Places API.
- Walking-time routing or transit-network routing.
- Advanced ML/recommendation models.
- Production scraping or automatic listing refresh.
- Crime/safety scoring.
- Marketing landing page or non-app first screen.

## Current Starting Point

- `app/streamlit_app.py` currently reads
  `property_explorer_gold.dim_property_listing` and
  `property_explorer_gold.dim_user_poi`.
- The current app has a basic PyDeck map, simple price/bed filters, POI category
  filtering, and setup-oriented empty behavior.
- Sprint 4 should change the primary app table to
  `property_explorer_gold.fct_property_context` and use the foundation
  dimensions for optional map layers and detail enrichment.

Current Sprint 2 foundation counts:

| Table | Current Count |
| --- | ---: |
| `property_explorer_gold.dim_property_listing` | 22 |
| `property_explorer_gold.dim_user_poi` | 206 |
| `property_explorer_gold.dim_tract_to_nta` | 2,327 |
| `property_explorer_gold.dim_subway_stop` | 496 |
| `property_explorer_gold.fct_tract_features` | 1,115 |
| `property_explorer_gold.fct_nta_features` | 108 |

Current Sprint 3 context result:

| Check | Current Result |
| --- | --- |
| `property_explorer_gold.fct_property_context` rows | 22 |
| Active context rows | 22 |
| Tract assignment | 22 / 22 |
| Missing NTA names | 0 |
| Missing subway distances | 0 |
| Subway distances over 2 miles | 0 |
| Score range violations | 0 |
| Neighborhood score status | all `unavailable` |
| Personal fit status | all `scored` |
| Total/property fit status | all `reweighted_missing_components` |

## Deliverables

- Streamlit app opens as Property Explorer, not NYC Property Finder.
- The first screen is the actual explorer: filters/sidebar, map, listing list,
  and selected property detail.
- Primary listing query reads from
  `property_explorer_gold.fct_property_context`.
- Listing markers are visible for active context rows with valid coordinates.
- Optional map layers for personal POIs and subway stops can be toggled.
- Listing cards show price, beds/baths, address, NTA, nearest subway distance,
  listing type/source, and score badges/statuses.
- Filters and sorting work from the app-ready context table without recomputing
  spatial joins.
- A selected property detail panel shows listing facts, source URL, score
  breakdown, missing-data explanations, transit context, and POI summary.
- Shortlist behavior is either implemented with persisted DuckDB writes or
  explicitly deferred within Sprint 4 after app read-only workflows are stable.
- App empty states explain missing database/table/data conditions.
- Focused tests cover app data queries, filtering/sorting helpers, score status
  presentation, shortlist persistence helpers if implemented, and no-data
  behavior.

## Acceptance Criteria

- `streamlit run app/streamlit_app.py` opens a usable local Property Explorer
  app against `data/processed/nyc_property_finder.duckdb`.
- The app does not fail when optional context tables are empty or missing; it
  shows clear setup/data messages instead.
- Active listings from `fct_property_context` appear on the map and in the
  listing list.
- Map/list/detail stay in sync when filters and sorting are applied.
- The app supports selecting one property from the list or map-driven workflow
  and shows a useful detail panel for that property.
- The UI clearly states that neighborhood metrics are currently unavailable
  when `neighborhood_score_status = 'unavailable'`.
- The UI shows that total/property fit scores are reweighted when
  `property_fit_score_status = 'reweighted_missing_components'`.
- Non-null score components are displayed on a `0-100` scale with component
  labels; null components are displayed as unavailable, not as zero.
- The app labels subway and POI proximity as straight-line MVP proxies.
- If shortlist writes are implemented, saving/removing/updating notes persists
  in `property_explorer_gold.fct_user_shortlist` and survives Streamlit refresh.
- `.venv/bin/pytest` passes after app helper tests are added.

## Detailed To-Dos

- [ ] Rename app page title and visible product name to Property Explorer.
- [ ] Replace the primary listing load with
  `property_explorer_gold.fct_property_context`, defaulting to `active = true`.
- [ ] Keep `dim_user_poi` and `dim_subway_stop` as optional layer queries.
- [ ] Add table availability checks for `fct_property_context`,
  `dim_user_poi`, `dim_subway_stop`, `fct_nta_features`, and
  `fct_user_shortlist`.
- [ ] Add a reusable app data module or helper functions for loading context,
  POIs, subway stops, shortlist rows, and NTA feature rows.
- [ ] Add defensive column normalization so the app can still render useful
  empty states if a table is missing expected optional columns.
- [ ] Build filter controls for listing facts, location, scores, transit
  distance, and POI categories.
- [ ] Build sort controls with stable deterministic tie-breaks.
- [ ] Build a map with property markers plus toggleable POI and subway layers.
- [ ] Use distinct, accessible map marker colors for properties, POIs, and
  subway stops.
- [ ] Add useful PyDeck tooltips for each layer.
- [ ] Add a listing list/card column that reflects the filtered and sorted
  dataset.
- [ ] Add selected property state using `st.session_state`, with a deterministic
  default selected property from the current filtered/sorted list.
- [ ] Add selected property detail view with listing, context, score, and
  missing-data sections.
- [ ] Add a compact POI category summary from `poi_category_counts` JSON.
- [ ] Add score display helpers that show numeric scores, status, and missing
  component text consistently.
- [ ] Add app copy for unavailable neighborhood metrics and reweighted total
  score behavior.
- [ ] Add source listing link behavior when `url` is present.
- [ ] Implement persisted shortlist save/remove/note update if it remains small
  and stable after read-only workflows are complete.
- [ ] If shortlist writes are deferred, keep a visible disabled or read-only
  placeholder out of the main workflow and document the exact remaining work.
- [ ] Add tests for filtering, sorting, score display/status logic, JSON POI
  category parsing, and shortlist persistence helpers if implemented.
- [ ] Run app smoke QA against the current 22-row database.

## App Table Dependencies

Sprint 4 should depend on the following tables and columns. New app features
should not require repeating Sprint 3 spatial joins in Streamlit.

### Primary Table: `property_explorer_gold.fct_property_context`

Required for Sprint 4 app workflows:

| Column | App Use |
| --- | --- |
| `property_id` | Selection key, card key, shortlist join. |
| `source` | Filter, card badge, detail source label. |
| `source_listing_id` | Detail/source diagnostics. |
| `address` | Card title, marker tooltip, detail header. |
| `lat`, `lon` | Map marker position. |
| `price` | Card primary fact, filter, sort. |
| `beds`, `baths` | Card facts, filters, sort. |
| `listing_type` | Filter and card badge; rentals and sales should be visibly distinct. |
| `active` | Default app filter. |
| `url` | Detail source link. |
| `ingest_timestamp` | Detail freshness/debug context. |
| `tract_id` | Detail/debug context. |
| `nta_id`, `nta_name` | Filter, card location, detail neighborhood. |
| `nearest_subway_stop` | Card/detail transit context. |
| `nearest_subway_distance_miles` | Filter, sort, card/detail transit context. |
| `subway_lines_count` | Mobility context/detail. |
| `poi_data_available` | Missing-data handling for POI/personal score. |
| `poi_count_nearby` | Card/detail POI context, sort/filter. |
| `poi_category_counts` | Detail POI summary and category-aware filtering. |
| `neighborhood_score` | Score breakdown; currently null/unavailable. |
| `neighborhood_score_status` | Required missing-data display. |
| `mobility_score` | Score badge, sort/filter, detail breakdown. |
| `personal_fit_score` | Score badge, sort/filter, detail breakdown. |
| `personal_fit_score_status` | Missing-data display if POIs are absent later. |
| `property_fit_score` | Default ranking/sort and detail total score. |
| `property_fit_score_status` | Required reweighted/missing-component display. |

Compatibility field:

| Column | App Use |
| --- | --- |
| `poi_count_10min` | Do not present as walking time; use only as a fallback alias for `poi_count_nearby` if needed. |

### Context Layers

`property_explorer_gold.dim_user_poi`:

| Column | App Use |
| --- | --- |
| `poi_id` | Layer row key. |
| `name` | Tooltip and layer legend. |
| `category` | Layer filter/color and detail category labels. |
| `source_list_name` | Tooltip and optional filter. |
| `lat`, `lon` | Map marker position. |

`property_explorer_gold.dim_subway_stop`:

| Column | App Use |
| --- | --- |
| `subway_stop_id` | Layer row key. |
| `stop_name` | Tooltip. |
| `lines` | Tooltip and detail context. |
| `lat`, `lon` | Map marker position. |

`property_explorer_gold.fct_nta_features`:

| Column | App Use |
| --- | --- |
| `nta_id`, `nta_name` | Optional selected-property neighborhood panel join. |
| `median_income`, `median_rent`, `median_home_value`, `pct_bachelors_plus`, `median_age` | Detail metrics only when non-null; show unavailable state when null. |

`property_explorer_gold.fct_user_shortlist`:

| Column | App Use |
| --- | --- |
| `shortlist_id` | Persistent row key. |
| `user_id` | Local user scope from `config/settings.yaml`. |
| `property_id` | Join to current context. |
| `saved_timestamp`, `updated_timestamp` | Detail/shortlist metadata. |
| `status` | Active/archived/rejected workflow. |
| `notes` | User notes. |
| `metadata_json` | Optional lightweight UI metadata. |

## Proposed Screens And Layout

Sprint 4 should keep the app to one direct explorer screen rather than adding
navigation or a landing page.

Recommended desktop layout:

- Sidebar: filters, sort, layer toggles, and data status.
- Main top band: compact metrics for visible listings, price range, active
  shortlist count, and data freshness if useful.
- Main left/center: map showing filtered property markers and optional context
  layers.
- Main right: selected property detail panel.
- Below map or in a left column: filtered/sorted listing cards.

Recommended mobile/narrow behavior:

- Sidebar filters remain collapsible.
- Map appears first.
- Listing cards follow the map.
- Detail appears after card selection.

Interactions:

- Filtering updates map, listing cards, and selected default.
- Sorting updates card order and the default selected row when the current
  selection falls out of the filtered set.
- Selecting a listing card updates the detail panel.
- A selected property should be visually identifiable in the list and, if
  feasible with PyDeck, in the marker styling.
- Layer toggles should not change listing filters; they only control map
  context visibility.
- The app should continue to work with 22 listings without pagination, but the
  list helper should be written so a later limit/pagination control is easy.

## Filter And Sort Requirements

Required filters:

- Active listings only by default, with an optional control to include inactive
  rows if present.
- Listing type: rental, sale, or both.
- Source: one or more source labels.
- Price range.
- Minimum beds.
- Minimum baths.
- NTA/neighborhood multi-select.
- Maximum straight-line subway distance.
- Minimum property fit score, with null-safe behavior.
- Minimum mobility score.
- Minimum personal fit score.
- POI category presence from `poi_category_counts`.
- Shortlist status filter if persisted shortlist is implemented.

Required sorts:

- Best overall fit: `property_fit_score` descending, nulls last.
- Highest personal fit: `personal_fit_score` descending, nulls last.
- Best mobility: `mobility_score` descending, nulls last.
- Nearest subway: `nearest_subway_distance_miles` ascending, nulls last.
- Lowest price: `price` ascending.
- Highest price: `price` descending.
- Most beds: `beds` descending.
- Neighborhood then price: `nta_name` ascending, `price` ascending.

Sort tie-breaks should use `price`, then `address`, then `property_id` so card
order is stable.

## Listing Card Requirements

Each listing card should show:

- Price, beds, baths, and listing type.
- Address.
- NTA name.
- Nearest subway stop and straight-line distance.
- Property fit, mobility, and personal fit score badges when available.
- Neighborhood score status when unavailable.
- Total score status when reweighted.
- Source label and source link action when `url` is present.
- Shortlist action if persistence is implemented.

Cards should avoid treating rentals and sales as directly comparable investment
opportunities. Listing type should be visible enough that mixed ranking is easy
to understand.

## Property Detail Requirements

The selected property detail should include:

- Address, price, beds, baths, listing type, and source.
- Source URL button/link when present.
- NTA name, tract ID, and NTA ID in a compact context area.
- Nearest subway stop, straight-line distance in miles, and subway line count.
- Nearby personal POI count and category-count summary.
- Score breakdown:
  - `property_fit_score`
  - `mobility_score`
  - `personal_fit_score`
  - `neighborhood_score`
- Score statuses:
  - `neighborhood_score_status`
  - `personal_fit_score_status`
  - `property_fit_score_status`
- NTA feature metrics only when non-null. With current data, the detail view
  should show that neighborhood metrics are unavailable instead of blank metric
  cards.
- Shortlist controls and notes if persistence is implemented.

## Score Explanation And Missing-Data Display

Score display rules:

- Scores are `0-100` when non-null.
- Null scores should display as "Unavailable" or equivalent text, never `0`.
- `neighborhood_score_status = 'unavailable'` should display an explanation
  that the current Metro Deep Dive NYC tract metrics are unavailable, so
  neighborhood scoring is intentionally not computed.
- `personal_fit_score_status = 'scored'` should display that the score uses
  loaded Google Maps personal POIs and straight-line nearby counts.
- `personal_fit_score_status = 'unavailable'` should display that POI data is
  absent, not that the property has no nearby fit.
- `property_fit_score_status = 'reweighted_missing_components'` should display
  that the total score is computed from available components and is missing
  neighborhood scoring under the current data.
- All proximity language should say straight-line distance or MVP proximity
  proxy. Do not label POI counts as walking-time or 10-minute access in the UI.

The app can include a compact score explanation expander in the detail panel,
but the critical statuses should be visible without requiring the user to hunt.

## Shortlist Requirements

Shortlists are an MVP data contract, but Sprint 4 should implement them in two
phases so the map/list/detail workflow is not blocked by write complexity.

Phase 1, required:

- Read active shortlist rows for the configured local user when
  `fct_user_shortlist` exists.
- Join shortlist status to context rows for card/detail badges.
- Show a data-safe empty state when no shortlist rows exist.

Phase 2, implement in Sprint 4 if low-risk:

- Save a selected listing to `fct_user_shortlist` with status `active`.
- Remove/archive a listing by setting status to `archived`, not deleting the
  row.
- Optional reject action sets status to `rejected`.
- Notes field can be edited from the detail panel.
- Use `config/settings.yaml` `local_user.default_user_id` as the MVP user ID.
- Generate `shortlist_id` deterministically from `user_id` and `property_id`,
  or use a UUID while preserving one current row per pair.
- Update `updated_timestamp` on status/note changes.

Defer within Sprint 4 if it threatens the core app:

- Side-by-side comparison view.
- Multi-user management UI.
- Shortlist history/events.
- Complex note metadata.

If Phase 2 is deferred, Sprint 4 should still document the exact write helper
API and UI placement for Sprint 5.

## Dependencies And Open Inputs

Dependencies:

- Completed Sprint 2 foundation tables in
  `data/processed/nyc_property_finder.duckdb`.
- Completed Sprint 3 context build with 22 context rows.
- `property_explorer_gold.fct_property_context` columns listed above.
- `config/settings.yaml` `local_user.default_user_id` for shortlist scope.
- Streamlit and PyDeck dependencies from the existing environment.

Open inputs:

- Confirm preferred shortlist behavior for the first app: save/archive only, or
  save/archive/reject plus notes.
- Confirm whether NTA feature metrics should be shown as a disabled/unavailable
  detail section in Sprint 4, or hidden until a non-null feature source exists.
- Confirm whether rentals and sales should default to both visible or rentals
  only for the first demo.
- Confirm preferred default sort. Proposed default:
  `property_fit_score` descending, nulls last.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Current neighborhood metrics are all null, making the app look incomplete. | Make missing neighborhood metrics a visible data-quality status and let mobility/personal fit carry the demo. |
| `property_fit_score` looks overly authoritative while reweighted. | Show the reweighted status next to the total score and expose component scores. |
| PyDeck click/selection behavior is awkward in Streamlit. | Make listing-card selection the reliable primary selection path; use map tooltips for context. |
| Mixed rentals and sales confuse price sorting and fit ranking. | Keep listing type filters prominent and show listing type on every card/detail header. |
| Shortlist writes add state bugs or DuckDB locking issues. | Implement read-only shortlist join first; add writes only after core app is stable. |
| POI category filtering from JSON is brittle. | Parse `poi_category_counts` with a helper that treats invalid or empty JSON as `{}` and test it. |
| App fails on a partially built database. | Centralize table availability checks and return empty DataFrames with clear setup messages. |
| Small 22-row sample hides edge cases. | Add fixture tests for empty tables, null scores, invalid JSON, and missing optional columns. |

## Deferred To Sprint 5

- Side-by-side shortlist comparison.
- Polished shortlist management view.
- One-command end-to-end app launch/rebuild workflow if it is not already in
  place.
- Expanded fixture-backed app smoke tests after the first UI implementation
  settles.
- Optional NTA boundary polygon layer if simple point layers are enough for
  Sprint 4.
- More complete source freshness indicators and rebuild buttons.

## Deferred Post-MVP

- Google Places API.
- Walking-time routing, transit routing, or network travel-time calculations.
- Advanced ML, learned preferences, or recommendation models.
- Production scraping and automated listing refresh.
- Crime/safety scoring or safety-themed ranking.
- Listing image/media ingestion.
- Manual POI category override UI.
- Authentication, cloud persistence, or multi-user account management.

## Test Coverage Needed

- Unit tests for app query helpers when tables exist, are missing, or are empty.
- Unit tests for filtering by price, beds, baths, listing type, source, NTA,
  score thresholds, subway distance, and POI category presence.
- Unit tests for sort options with null-safe ordering and deterministic
  tie-breaks.
- Unit tests for parsing `poi_category_counts` JSON.
- Unit tests for score/status display helpers, especially null neighborhood
  score and reweighted total score.
- Unit tests for selected-property fallback when the current selection is
  filtered out.
- Unit tests for shortlist ID generation and status/note upsert helpers if
  Sprint 4 implements writes.
- A lightweight app smoke test or script that imports `app/streamlit_app.py`
  helper functions without launching Streamlit.

## Data And App QA Before Completion

Data QA:

- `fct_property_context` row count is 22.
- Active context row count is 22.
- Every active context row has non-null `property_id`, `address`, `lat`, `lon`,
  `price`, `beds`, `baths`, and `listing_type`.
- Every active context row has non-null `nta_name`.
- Every active context row has non-null `nearest_subway_distance_miles`.
- No active context row has `nearest_subway_distance_miles > 2` unless reviewed.
- `poi_category_counts` parses as JSON for every row.
- Non-null score values are between `0` and `100`.
- `neighborhood_score_status` is displayed as unavailable for current rows.
- `property_fit_score_status = 'reweighted_missing_components'` is displayed
  clearly for current rows.

App QA:

- App loads with the current local database.
- App shows all 22 active listings before filters.
- Price, bed, listing type, NTA, subway distance, score, and POI category
  filters update both the map and list.
- Every sort option produces a stable card order.
- Selecting each listing from the visible list updates the detail panel.
- POI layer toggle shows/hides Google Maps POIs without changing listing
  filters.
- Subway layer toggle shows/hides subway stops without changing listing
  filters.
- Detail panel shows source URL links when present.
- Detail panel does not display null neighborhood metrics as zeros.
- Shortlist actions persist after browser refresh if write behavior is
  implemented.
- With a renamed/missing database file, the app shows setup guidance instead of
  crashing.
- With empty POI or subway tables, the app still supports listing review and
  explains missing layers.
