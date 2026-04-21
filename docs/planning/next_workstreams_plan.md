# Property Explorer Next Workstreams Plan

This plan captures the post-Sprint 4 workstreams needed to make Property
Explorer more complete and credible after the first usable map/list/detail app.

## Review Agenda

Use this doc to decide which workstream to run next. The current candidate
workstreams are:

1. ACS neighborhood census context.
2. Scoring redesign or score de-emphasis.
3. Google Places API POI enrichment with one-time cached calls.
4. StreetEasy scraper as a real listing-source adapter.
5. Additional product/data hardening that may otherwise sneak up on us:
   rebuild orchestration, app QA, rental/sale modes, data freshness, shortlist
   comparison, NTA map layers, and privacy review.

Review questions:

- Do we want to run ACS first so the app stops showing unavailable neighborhood
  metrics?
- Should total/property fit stay visible as experimental, move out of the
  default sort, or be hidden until the scoring redesign?
- Which Google Maps lists should be cleaned up before we pay for Google Places
  enrichment?
- What StreetEasy run modes are acceptable: fixture parser only, manual saved
  HTML, limited live fetch, or no live fetch until access rules are clearer?
- Which missing product surface matters most for actual use: shortlist
  comparison, rental/sale mode separation, or data freshness?

## Current Shortlist Persistence

Shortlist actions in the Streamlit app persist to the local DuckDB database:

- Database path: `data/processed/nyc_property_finder.duckdb`
- Table: `property_explorer_gold.fct_user_shortlist`
- User scope: `config/settings.yaml` `local_user.default_user_id`

Current columns:

| Column | Purpose |
| --- | --- |
| `shortlist_id` | Stable ID generated from `user_id` and `property_id`. |
| `user_id` | Local user identifier, currently `local_default` unless config changes. |
| `property_id` | Joins to `property_explorer_gold.fct_property_context`. |
| `saved_timestamp` | First time saved. |
| `updated_timestamp` | Latest status or notes change. |
| `status` | `active`, `archived`, or `rejected`. |
| `notes` | User notes from the property detail panel. |
| `metadata_json` | Reserved for lightweight app metadata. |

Useful inspection query:

```sql
SELECT *
FROM property_explorer_gold.fct_user_shortlist
ORDER BY updated_timestamp DESC;
```

## Workstream 1: ACS Neighborhood Census Context

Goal: replace null neighborhood metrics with tract-level ACS data, mapped to
NTAs/neighborhoods, so the app can display real neighborhood context and a
better future neighborhood score.

### Recommended Approach

Use ACS 5-year tract data as the source of truth for census context.

1. Select ACS subject/profile/detail variables.
2. Pull tract-level ACS data for NYC counties.
3. Normalize ACS variables into
   `property_explorer_gold.fct_tract_features`.
4. Join tracts to NTAs through
   `property_explorer_gold.dim_tract_to_nta`.
5. Aggregate tract metrics to
   `property_explorer_gold.fct_nta_features`.
6. Optionally materialize NTA geometries or derived neighborhood geometry for
   map overlays.
7. Rebuild `property_explorer_gold.fct_property_context`.
8. Update the app detail view to display non-null NTA metrics.

### Geography Strategy

Keep tract geography and NTA geography conceptually separate:

- Use tract polygons for property assignment and tract-level ACS joins.
- Use the official tract-to-NTA equivalency table for tract-to-neighborhood
  membership.
- Use official NTA boundary GeoJSON for neighborhood map overlays when possible.
- Only derive neighborhood geometry from tract geometries if official NTA
  geometry is unavailable or mismatched. If deriving, dissolve tract polygons by
  `nta_id` after confirming tract coverage and CRS.

### ACS Variable Candidates

MVP neighborhood context:

| Metric | Example ACS Concept | Notes |
| --- | --- | --- |
| Median household income | ACS 5-year detailed/profile income variable | Store USD. |
| Median gross rent | ACS 5-year housing/rent variable | Store USD/month. |
| Median home value | ACS 5-year owner-occupied value variable | Store USD. |
| Percent bachelor's plus | ACS education attainment variables | Store consistently as `0-100` or document `0-1`; prefer `0-100` in final table. |
| Median age | ACS age variable | Store years. |

Good next metrics for app context, not necessarily scoring:

- Rent-burden share.
- Share renter-occupied.
- Vacancy rate.
- Commute mode/transit share.
- Household size.
- Population density if area is available.

Crime/safety remains deferred.

### Implementation To-Dos

- [ ] Decide ACS vintage, likely latest ACS 5-year available.
- [ ] Add Census source config for API endpoint, vintage, variables, and NYC
  county GEOIDs.
- [ ] Add optional `CENSUS_API_KEY` support, while allowing no-key use where
  Census API limits permit.
- [ ] Implement ACS tract pull/cache under `data/raw` or `data/interim`.
- [ ] Normalize tract IDs to full GEOID strings matching `dim_tract_to_nta`.
- [ ] Add variable metadata documentation so metric formulas are traceable.
- [ ] Replace or supplement the current Metro Deep Dive placeholder path.
- [ ] Aggregate tract features to NTA features with documented aggregation
  rules.
- [ ] Add QA queries for row counts, tract join rates, null rates, and metric
  ranges.
- [ ] Rebuild `fct_property_context` and confirm neighborhood score status is
  no longer all `unavailable` when metrics are populated.

### Aggregation Rules

Default MVP aggregation:

- Median-like ACS values: tract median across NTA as a first pass, clearly
  documented as an approximation.
- Percent/share metrics: population- or household-weighted average when
  denominators are available.
- Counts: sum.

Better version:

- Pull numerator and denominator variables where possible.
- Compute NTA ratios from summed numerator/denominator, not median of tract
  ratios.
- Avoid pretending that median-of-medians is a true NTA median.

### Acceptance Criteria

- `fct_tract_features` has non-null ACS metrics for Manhattan/Brooklyn tracts.
- `fct_nta_features` has non-null metrics for NTAs containing current listings.
- Every current property can display NTA-level census context.
- ACS metric units and formulas are documented.
- Null rates and outlier ranges are reviewed before using metrics in scoring.

## Workstream 2: Scoring Redesign

Goal: pause or de-emphasize the current MVP score until the inputs and formulas
are credible, then redesign scoring around transparent user decisions.

### Current State

Current scoring is intentionally simple:

- Config weights in `config/scoring_weights.yaml`:
  - neighborhood: `0.40`
  - mobility: `0.25`
  - personal fit: `0.35`
- Neighborhood score uses income, rent, and education when available.
- Mobility score uses nearest subway straight-line distance and line count.
- Personal fit score uses nearby Google Maps saved POI counts and category
  diversity.
- Total/property fit reweights across available components and marks missing
  components.

This is useful for wiring the product but not yet product-grade.

### Recommendation

Archive or down-rank the total score as an MVP technical artifact until ACS,
POI, and listing quality improve.

Near-term app behavior:

- Keep component scores visible only where inputs are credible.
- Keep total fit labeled as experimental or hide it from default sorting if it
  starts misleading review.
- Prefer transparent sortable facts: price, subway distance, POI count,
  personal category matches, beds/baths, and NTA.

### Redesign Questions

- Are rentals and sales scored separately?
- Is the primary decision affordability, lifestyle fit, commute access, or
  neighborhood quality?
- Should the user provide preference weights in the UI?
- Which POI categories should be positive, neutral, or negative?
- Should high median income/home value be interpreted as desirable, expensive,
  or both?
- Should neighborhood score be an explanation panel rather than a ranking
  component?

### Implementation To-Dos

- [ ] Add a scoring design doc before changing formulas.
- [ ] Split rental and sale scoring assumptions.
- [ ] Define component inputs, directionality, units, and missing-data behavior.
- [ ] Add a version field or metadata file for score formula versioning.
- [ ] Add test fixtures with expected scores for clear scenarios.
- [ ] Consider app preference controls for user weights after core formulas are
  stable.
- [ ] Decide whether `property_fit_score` remains default sort or becomes an
  optional/experimental sort.

### Acceptance Criteria

- Score formulas are documented enough to explain to a user.
- Component scores match intuitive fixture cases.
- Missing data never silently becomes zero.
- Total score is not displayed without visible component/status context.

## Workstream 3: Google Places API POI Enrichment

Goal: improve POI quality by resolving Google Maps saved-list places to stable
Google Places records once, caching the results, and avoiding repeated paid API
calls.

### Recommended Approach

Keep Google Maps saved lists as the user curation source, then enrich them:

1. Improve Google Maps lists manually so they reflect real preferences.
2. Parse saved-list CSV exports as the input queue.
3. Extract place names and Google Maps URLs.
4. Resolve each unresolved place through Google Places API.
5. Store raw and normalized API results locally.
6. Never call the API again for a place that already has a cached `place_id` and
   detail payload unless explicitly refreshed.
7. Build `dim_user_poi` from the cached normalized table.

### Proposed Local Tables/Artifacts

Raw/cache artifacts:

- `data/interim/google_places/place_resolution_cache.parquet` or CSV.
- `data/interim/google_places/place_details_raw.jsonl`.
- `data/interim/google_places/place_resolution_quarantine.csv`.

Possible DuckDB tables:

| Table | Grain | Purpose |
| --- | --- | --- |
| `property_explorer_gold.dim_user_poi` | One app-ready POI | Existing app table. |
| `property_explorer_gold.dim_google_place_cache` | One resolved Google place | Optional persisted cache mirror. |

Cache fields:

- `source_list_name`
- `input_name`
- `input_url`
- `google_place_id`
- `display_name`
- `formatted_address`
- `lat`
- `lon`
- `google_primary_type`
- `google_types_json`
- `rating`
- `user_rating_count`
- `price_level`
- `business_status`
- `last_fetched_timestamp`
- `raw_response_path` or `raw_response_json`

### API Cost Controls

- Require an explicit command to call Google Places API.
- Default pipelines should use cache-only mode.
- Add a `--refresh-missing-only` mode.
- Add a `--limit` option for test runs.
- Add a dry-run that prints unresolved count and expected calls.
- Write cache after every successful call so interrupted runs do not repeat
  completed work.
- Keep API keys in environment variables, not committed config.

### Implementation To-Dos

- [ ] Decide Places API endpoint and fields needed.
- [ ] Add `GOOGLE_PLACES_API_KEY` environment variable handling.
- [ ] Add cache schema and read/write helpers.
- [ ] Add resolver that first checks cache by input URL/name and then by
  `place_id`.
- [ ] Add quarantine for ambiguous or failed matches.
- [ ] Normalize Google types into existing POI categories while preserving raw
  Google type metadata.
- [ ] Update POI ingestion runbook to support cache-only and API-refresh modes.
- [ ] Add tests with mocked API responses.

### Acceptance Criteria

- Existing saved-list CSVs can be enriched without repeated paid calls.
- A second run with the same inputs makes zero API calls.
- Every app POI has stable coordinates and, where resolved, a Google Place ID.
- Failed/ambiguous places are quarantined for review.

## Workstream 4: StreetEasy Scraper

Goal: build a real StreetEasy ingestion adapter that can populate the manual
listing contract while respecting operational and legal constraints.

### Current State

`src/nyc_property_finder/scrapers/streeteasy.py` is a skeleton that returns an
empty structured DataFrame. It exists to define the interface, not to scrape
yet.

### Recommended Approach

Treat StreetEasy as a source adapter feeding the same listing contract, not as a
parallel app path.

Phases:

1. Source/access review.
2. Saved search URL fetching.
3. HTML capture and fixture storage.
4. Parser implementation against saved HTML fixtures.
5. Respectful live fetch with throttling and limits.
6. Normalization into `dim_property_listing`.
7. Geocoding fallback for listings with hidden/approximate coordinates.
8. QA/quarantine for incomplete listings.

### Safety And Operational Constraints

- Review robots/terms before live scraping.
- Use manual/saved HTML fixtures for parser tests.
- Add request throttling, user-agent config, and hard limits.
- Avoid login-protected or anti-bot circumvention.
- Keep scraper optional; manual CSV remains the fallback ingestion path.
- Persist raw HTML snapshots only locally and avoid committing them.

### Listing Fields To Extract

Minimum:

- `source_listing_id`
- `address` or display title
- `price`
- `beds`
- `baths`
- `listing_type`
- `url`
- `neighborhood_label`
- `borough`

Strong next fields:

- `lat`, `lon` if exposed in page data.
- `unit`
- `sqft`
- `available_date`
- `no_fee`
- `broker_fee`
- `amenities`
- `description`
- `source_updated_at`
- `coordinate_quality`

### Implementation To-Dos

- [ ] Add a scraper design doc with access rules and allowed run modes.
- [ ] Create fixture HTML directory under ignored local data or checked-in
  sanitized test fixtures.
- [ ] Implement parser functions independent of network requests.
- [ ] Add parser tests for search result pages and listing detail pages.
- [ ] Implement live fetch with throttling and `limit`.
- [ ] Normalize parser output into the manual listing contract.
- [ ] Add geocode fallback for rows missing coordinates.
- [ ] Add quarantine output for missing price/address/coordinates after
  fallback.
- [ ] Add runbook commands and warnings.

### Acceptance Criteria

- Parser tests pass from static StreetEasy fixtures.
- Live fetch, if enabled, respects limits and does not run by default in tests.
- Output rows normalize into `property_explorer_gold.dim_property_listing`.
- Rows without map-safe coordinates are geocoded or quarantined.

## What We Might Be Missing

These are not as urgent as ACS, scoring, POI quality, and StreetEasy, but they
will matter soon:

### Rebuild Orchestration

The project needs one command or short command sequence that runs the complete
local build:

1. Initialize DuckDB.
2. Build foundation tables.
3. Build ACS neighborhood context.
4. Build/enrich POIs from cache.
5. Build property context.
6. Run QA checks.
7. Optionally launch Streamlit.

Without this, each workstream can succeed in isolation while the full product
remains hard to refresh.

### App QA Harness

The app should eventually have a fixture database plus a smoke test that checks:

- App imports cleanly.
- Required tables can be absent without crashes.
- Context rows render through filters/sorts/detail.
- Shortlist writes persist in a temp database.
- Map layer construction returns non-empty layers when data exists.

This does not need full visual regression testing yet, but it should catch
broken app contracts before manual review.

### Rental Vs Sale Review Modes

Rentals and sales share the current listing table, but their decision logic is
different. We likely need explicit app modes:

- Rental mode: monthly price, no-fee/broker-fee, availability, commute/lifestyle
  fit.
- Sale mode: purchase price, home value context, long-term neighborhood
  context, and possibly carrying costs later.

Until then, mixed sorting can be misleading even if listing type is visible.

### Data Freshness And Build Provenance

The app should eventually show when each major input was last built:

- Listing file/scrape timestamp.
- POI export and Google Places cache age.
- ACS vintage.
- Subway GTFS vintage.
- Property context build timestamp.

This helps distinguish "bad property" from "stale data."

### Shortlist Comparison

The current shortlist stores status and notes, but the next useful product
surface is side-by-side comparison of active shortlist rows:

- Price, beds/baths, listing type.
- NTA and neighborhood metrics.
- Subway access.
- POI category counts.
- Notes/status.
- Source links.

This can wait until the data context is stronger, but it is likely the next
major app feature after review mode stabilizes.

### NTA Map Layer

The map currently shows points. A neighborhood layer would make census context
more legible:

- Prefer official NTA boundary GeoJSON.
- Use tract-dissolved NTA geometry only if official NTA geography is unavailable
  or mismatched.
- Avoid rendering huge geometry by default if it slows the app; make it a
  toggle.

### Privacy And Local Data Policy

Several future artifacts are sensitive and should stay local:

- Raw Google Maps exports.
- Google Places cache and raw responses.
- Listing notes/shortlist rows.
- Raw StreetEasy HTML captures.
- Real listing URLs and exact addresses if the repo is shared.

The repo should continue to keep raw/source data ignored and document what is
safe to commit.

### Source Terms And Operational Risk

StreetEasy scraping carries more risk than ACS or Google Places cache work. We
should explicitly decide:

- What access modes are allowed.
- Whether live scraping is acceptable at all.
- Whether manual saved HTML is enough for the next milestone.
- How to keep tests from making live network requests.

### Data Model Evolution

Likely table additions after the next workstreams:

| Candidate Table | Purpose |
| --- | --- |
| `property_explorer_gold.dim_google_place_cache` | Persist resolved Google Place IDs/details and avoid repeated API calls. |
| `property_explorer_gold.dim_nta_geometry` | Optional NTA map layer geometry. |
| `property_explorer_gold.dim_score_version` or config artifact | Track scoring formula versions. |
| `property_explorer_gold.fct_build_run` | Track pipeline run timestamps, counts, and QA status. |
| Listing source/raw capture tables or files | Preserve scraper/parser input provenance without changing app contracts. |

## Suggested Execution Order

1. ACS neighborhood context.
2. Scoring redesign or score de-emphasis decision.
3. Google Places cached enrichment.
4. StreetEasy scraper.
5. Shortlist comparison and app polish.

Reasoning:

- ACS fixes the biggest current data gap and unlocks real neighborhood context.
- Scoring should not be refined too deeply before ACS and POI quality are
  better, but the product should decide whether to hide/de-emphasize totals now.
- Google Places improves personal context quality and category reliability.
- StreetEasy expands listing supply, but it carries the most operational risk,
  so it should be built as an optional adapter with manual CSV fallback.
