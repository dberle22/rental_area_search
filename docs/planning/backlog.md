# Stoop NYC — Backlog

Last updated: 2026-04-30

This is the active product backlog. Work is organized into sprints. Each task
is labeled `[agent]`, `[you]`, or `[you+agent]`.

WS1–WS6 are complete. See `docs/planning/workstreams.md` for the full historical
record of that work. The sprints below pick up from the current state of the
repo.

For product strategy and data product definitions see
`docs/planning/product_strategy.md`.

---

## Current State Snapshot

| Data Product | Status |
| --- | --- |
| Curated Places (`dim_user_poi_v2`) | Active — Google Takeout + 14 article scrapes loaded. Hotels, crowd upload pending. |
| City Baseline (`dim_public_poi`) | Complete — 56,540 rows, 27 categories. Hotels, crime, school quality pending. |
| Neighborhood Context (`fct_tract/nta_features`) | Active — five-borough geography live; full NTA metric coverage partial. |
| Property Listings (`dim_property_listing`) | Placeholder — 22-row sample only. |
| Shortlists (`fct_user_shortlist`) | Partial — property shortlist in on-ice Property Explorer V1. Neighborhood shortlist not built. |

| App | Status |
| --- | --- |
| Stoop Explore | Foundation live (`app/streamlit_app_v2.py`). Needs rebrand, intelligence layer, hotel category, and UX reframe. |
| Stoop Search | Not started as standalone app. Phase 1 buildable now after Sprint 1 data work. |
| Stoop Visit | Deferred. |

---

## Goals

These are the four strategic outcomes that the sprints below are working toward:

1. **Launch Stoop Explore publicly** — a credible neighborhood explorer for
   locals and day-trippers, with curated POI depth, hotel coverage, and a
   "where should I spend a day" intelligence layer.

2. **Launch Stoop Search Phase 1 publicly** — a standalone neighborhood
   livability app with crime, schools, transit, and demographic context for
   people evaluating where to live.

3. **Complete the data platform foundation** — all five data products at
   production quality: hotels in Curated Places and City Baseline, crime in
   City Baseline, school quality in City Baseline, crowd upload path live.

4. **Build Property Listings and Stoop Search Phase 2** — real listing data
   from StreetEasy and Zillow flowing into Stoop Search, with property-specific
   intelligence and shortlists.

---

## Sprint 1 — Data Platform Foundation

**Goal**: Complete the data platform before building new app surfaces. All new
data should flow through existing ingestion patterns where possible.

**Outcome**: City Baseline has hotels, crime, and school quality. Curated Places
has hotels. Crowd upload path is live.

### Hotels

- [ ] `[you+agent]` Decide hotel sourcing strategy: OSM pull (comprehensive
  baseline) vs. editorial scrape (Eater, Condé Nast — curated top picks). Both
  can coexist: OSM → City Baseline, editorial → Curated Places.
- [ ] `[agent]` Add `hotel` category to `dim_public_poi` from OSM NYC hotel
  data via the existing `osm.py` source module in Wave 3/4 pattern.
- [ ] `[agent]` Add `hotels` to `config/poi_categories.yaml` curated taxonomy
  and identify one editorial source article (e.g. Eater or Condé Nast best
  hotels NYC) to register in `config/curated_scrape_articles.yaml`.
- [ ] `[you]` Save the target editorial hotel article HTML locally and run the
  parser; review normalized CSV before Places resolve.
- [ ] `[agent]` Run hotel article through `ingest_curated_poi_web_scrape`,
  review QA outputs, mark `loaded` in config.

### Crime

- [ ] `[agent]` Identify the best NYC Open Data crime dataset: NYPD Complaint
  Data (historic) or NYPD Shooting Incident Data, and confirm the API endpoint
  and field contract.
- [ ] `[you]` Review the identified dataset and approve the field contract before
  ingestion is built.
- [ ] `[agent]` Build a crime ingestion module under `public_poi/sources/` or a
  new `neighborhood_context/` package (decide based on whether crime is a point
  layer or an NTA-level aggregate).
- [ ] `[agent]` Write crime data to a new gold table or extend
  `fct_nta_features` with an NTA-level crime rate metric. Update
  `docs/data_model.md` and DDL accordingly.
- [ ] `[agent]` Add crime coverage to the QA app panel.
- [ ] `[you]` Review crime data quality in QA app before proceeding.

### School Quality

- [ ] `[agent]` Identify the NYC DOE dataset that provides school-level quality
  signals (School Quality Reports or Progress Reports) and confirm the source
  URL and field contract.
- [ ] `[you]` Approve the DOE field contract and decide the grain: keep as point
  data (school locations + quality score) or aggregate to NTA level.
- [ ] `[agent]` Build school quality ingestion; extend `dim_public_poi` with a
  quality score field for `public_school` rows, or write a separate
  `dim_school_quality` table if the grain warrants it.
- [ ] `[agent]` Update `docs/data_model.md` and DDL for any schema additions.
- [ ] `[you]` Review school quality data in QA app before proceeding.

### Crowd / Excel Upload (WS7)

- [ ] `[you]` Define the submission template fields: at minimum name, address
  (optional), URL, category, submitter notes.
- [ ] `[you+agent]` Design the normalization pipeline: template → normalize →
  Places resolve → `stg_user_poi_manual_upload` → canonical merge into
  `dim_user_poi_v2`. Must use staged-accumulation pattern (new batches merge
  with existing staging rows, not replace them).
- [ ] `[agent]` Implement template reader and normalization module under
  `curated_poi/excel_upload/`.
- [ ] `[agent]` Implement `stg_user_poi_manual_upload` staging writer and
  canonical merge promotion path following the same pattern as
  `stg_user_poi_web_scrape`.
- [ ] `[agent]` Build CLI entry point: `pipelines/ingest_curated_poi_manual_upload.py`.
- [ ] `[agent]` Document the submission workflow in `docs/user_guide.md` and
  `docs/poi_categories.md`.
- [ ] `[you]` Test with a small sample submission CSV before signing off.

---

## Sprint 2 — Stoop Explore V1 Launch

**Goal**: Rebrand and polish the current Neighborhood Explorer into Stoop
Explore with a clear "where should I spend a day" intelligence layer, hotel
coverage, and a public launch.

**Outcome**: Stoop Explore is live on Streamlit Cloud, announced on LinkedIn,
Reddit, and Substack.

### Rebrand and Docs Alignment

- [ ] `[agent]` Rename app entry point from `streamlit_app_v2.py` to
  `app/stoop_explore.py` (or add alias). Update Streamlit Cloud config.
- [ ] `[agent]` Update `docs/architecture.md`, `docs/README.md`,
  `docs/app/neighborhood_explorer_app.md`, and `docs/planning/product_strategy.md`
  to use Stoop Explore naming consistently.
- [ ] `[agent]` Update `docs/data_model.md` "Current App Consumption" table to
  reflect Stoop Explore and Stoop Search as the two primary apps.

### Intelligence Layer

- [ ] `[you+agent]` Design the neighborhood character panel: what fields to show,
  what the "best neighborhoods for X" ranking should look like, how it anchors to
  the primary question.
- [ ] `[agent]` Add neighborhood character summary panel to Stoop Explore:
  dominant POI categories for the selected NTA, top-3 curated places by
  category, key demographic tone (income band, median age).
- [ ] `[agent]` Add "Top neighborhoods for [category]" ranking surface: sidebar
  or panel that ranks NTAs by curated POI density for the currently selected
  category filter.
- [ ] `[agent]` Add hotel POI layer to Stoop Explore once Sprint 1 hotel
  ingestion is complete.

### UX Polish

- [ ] `[you]` Full UX review pass: walk through the "where should I spend
  Saturday in NYC" workflow and note anything broken, confusing, or missing.
- [ ] `[agent]` Implement agreed UX fixes from review.
- [ ] `[you]` Final sign-off before launch.

### Public Launch

- [ ] `[you]` Write LinkedIn post, Reddit post, Substack intro announcing Stoop
  Explore.
- [ ] `[you]` Monitor early feedback and log actionable items.

---

## Sprint 3 — Stoop Search Phase 1

**Goal**: Build a standalone app that answers "is this neighborhood somewhere I
would like to live?" using the livability data from Sprint 1.

**Outcome**: Stoop Search Phase 1 is live with crime, schools, transit, grocery,
and demographic context visible per neighborhood.

### App Foundation

- [ ] `[you+agent]` Design Stoop Search Phase 1: which panels, what the
  neighborhood livability summary looks like, what the comparison view shows.
- [ ] `[agent]` Create `app/stoop_search.py` as a new Streamlit entry point
  sharing the same data product layer as Stoop Explore.
- [ ] `[agent]` Build livability panel per NTA: transit coverage (subway station
  count and lines within walk distance), grocery/pharmacy access, school
  proximity and quality score, crime context.
- [ ] `[agent]` Build neighborhood comparison view: select 2–3 NTAs and compare
  side by side on livability dimensions plus demographic metrics.
- [ ] `[agent]` Add livability scoring or ranking surface so the app helps
  answer "which neighborhoods score well on what I care about?" rather than just
  displaying raw data.

### Demographic Expansion

- [ ] `[agent]` Identify ACS variables for renter-occupied share, vacancy rate,
  population density, and transit commute share. Confirm they are available in
  the existing Metro Deep Dive source.
- [ ] `[you]` Approve the additional ACS metrics before ingestion.
- [ ] `[agent]` Add new metrics to `fct_tract_features`, `fct_nta_features`,
  DDL, pipeline, and QA checks.

### Launch

- [ ] `[you]` Full UX review: walk through "would I like living in Crown
  Heights?" workflow end to end.
- [ ] `[agent]` Implement agreed fixes from review.
- [ ] `[you]` Launch Stoop Search Phase 1.

---

## Sprint 4 — Shortlists MVP

**Goal**: Allow users to save neighborhoods and (eventually) properties with a
data model designed for future sharing.

**Outcome**: Neighborhood shortlist is live in Stoop Search with local
persistence. Property shortlist architecture is designed and ready for Phase 2.

### Design

- [ ] `[you+agent]` Lock the shortlist data model: fields for neighborhood saves
  (nta_id, nta_name, notes, saved_at, status), fields for property saves (to be
  finalized in Sprint 5), and the sharing model design (user identity approach).
- [ ] `[agent]` Remove shortlist UI from current app frontend (Property Explorer
  V1 is already on ice; confirm nothing in Stoop Explore surfaces shortlist
  features).

### Neighborhood Shortlist

- [ ] `[agent]` Add `fct_user_neighborhood_shortlist` table to DDL and data
  model.
- [ ] `[agent]` Implement neighborhood save/archive/note actions in Stoop Search.
- [ ] `[agent]` Add shortlist panel to Stoop Search sidebar: saved neighborhoods
  with notes, quick-compare shortcut.
- [ ] `[you]` Review shortlist UX.

### Sharing Architecture (Design Only)

- [ ] `[you+agent]` Design the user identity model needed for shared shortlists:
  what auth approach (email link, simple passcode, Streamlit auth), what the
  shared shortlist UX looks like, what the backend requirement is.
- [ ] Document the decision in `docs/decision_log.md`. Implementation is
  deferred to a future sprint.

---

## Sprint 5 — Property Listings + Stoop Search Phase 2

**Goal**: Real listing data from StreetEasy and Zillow flowing into Stoop Search
with property-specific intelligence and shortlists.

**Outcome**: Stoop Search Phase 2 shows real listings on the map, price vs. NTA
median, transit from listing, and a working property shortlist.

### Listing Parsers

- [ ] `[you]` Save 10–20 StreetEasy listing HTML pages locally under
  `data/raw/scraped/raw/streeteasy/`.
- [ ] `[you]` Save 10–20 Zillow listing HTML pages locally under
  `data/raw/scraped/raw/zillow/`.
- [ ] `[agent]` Inspect saved StreetEasy HTML and build parser: extract price,
  beds, baths, address, unit, no_fee, available_date, source URL. Normalize into
  `contracts/listing_csv_contract.md`.
- [ ] `[agent]` Inspect saved Zillow HTML and build parser with the same output
  contract.
- [ ] `[agent]` Build CLI entry points: `pipelines/ingest_property_streeteasy.py`
  and `pipelines/ingest_property_zillow.py`.
- [ ] `[you]` Review first normalized listing CSVs for each source before
  running geocoding and DuckDB load.
- [ ] `[agent]` Run parsers end to end: normalize → geocode → load
  `dim_property_listing` → build `fct_property_context`.

### Stoop Search Phase 2 App Layer

- [ ] `[agent]` Add listing map layer to Stoop Search: listing points sized or
  colored by price, filterable by beds and price range.
- [ ] `[agent]` Add listing detail panel: price vs. NTA median rent, subway
  lines within walk, grocery/pharmacy count nearby, curated POI density.
- [ ] `[agent]` Implement property shortlist in Stoop Search: save, archive, add
  notes. Follows the model from Sprint 4.
- [ ] `[you]` Full end-to-end review of Stoop Search Phase 2.
- [ ] `[you]` Launch Stoop Search Phase 2.

---

## Deferred

These are agreed future work items that are out of scope for the current sprints.

| Item | Reason deferred |
| --- | --- |
| Stoop Visit (out-of-town tourist app) | Build after Stoop Explore is live and validated. Needs hotel data and simpler UX. |
| Shared shortlists / user identity | Requires auth backend. Design in Sprint 4, implement when Phase 2 ships. |
| MotherDuck / hosted DuckDB | Not a blocker at current scale. Revisit when data volume or concurrent user load requires it. |
| Walking-time proximity (vs. straight-line) | Post-Phase 2. Routing API adds complexity. |
| Listing snapshot / price history | Post-Phase 2. Requires repeated scrape runs. |
| Itinerary / day-plan generation | Far future. Ranked POI lists serve the near-term need. |
| Multi-city expansion | After NYC apps are validated and stable. |
