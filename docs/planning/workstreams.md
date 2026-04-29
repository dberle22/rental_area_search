# Active Workstreams

Last updated: 2026-04-28

This is the current operating plan. Each workstream has clear to-dos labeled
by who does the work: `[agent]` = delegatable to an AI coding agent,
`[you]` = requires your decision or review, `[you+agent]` = design together
then implement.

For deeper background on any workstream see the doc links inline.
For the full pipeline build order see `docs/pipeline_plan.md`.
For POI category status see `docs/poi_categories.md`.

---

## Status Snapshot

| Domain | Status | Blocker |
| --- | --- | --- |
| Foundational Demographics | Done | None |
| Public POI baseline (`dim_public_poi`) | Data complete; not in app yet | Frontend wiring needed |
| Curated POI (`dim_user_poi_v2`) | WS2.5 migration slice landed | Multi-source staging writers still pending |
| Real Estate Listings | Placeholder only | Deferred by choice |
| Neighborhood Explorer V2 | Working; POI coverage narrow | Depends on WS2 + WS3 |
| QA App | Working; demographics + POI coverage panels live | Awaiting WS5 review sign-off |
| Intelligence Layer | Not started | Depends on WS2 + WS3 + WS4 |

---

## WS1 — Curated POI Taxonomy + Batch Pipeline

**Goal**: Make `data/raw/google_maps/poi_nyc/` the canonical curated POI source
and update the curated POI pipeline so it supports a real taxonomy model
(`category`, `subcategory`, and optional deeper taxonomy), normalizes all
source CSVs consistently, and ingests the full directory in one run. Right now
the CLI still accepts a single CSV path and category assignment is too flat for
restaurant-style sub-lists.

**Depends on**: nothing. Do this first.

- [x] `[you+agent]` Lock the curated POI taxonomy in `docs/poi_categories.md`:
  top-level `category`, second-level `subcategory`, and an optional deeper
  level when needed
- [x] `[agent]` Update the curated POI data model and pipeline contract so
  `dim_user_poi_v2` carries explicit taxonomy fields while preserving current
  compatibility fields used by the app
- [x] `[agent]` Add normalization rules for `data/raw/google_maps/poi_nyc/`
  that assign `category` and `subcategory` from the filename, `Tags`, and
  `Comment` fields as appropriate
- [x] `[agent]` Normalize restaurant-family files so cuisine- or format-
  specific lists roll up under `category=restaurants` with drill-down handled
  by `subcategory` or deeper taxonomy
- [x] `[agent]` Add a `--input-dir` mode to `ingest_google_places_poi.py` that
  globs `*.csv` from a directory, processes all files, and writes one combined
  `dim_user_poi_v2`
- [x] `[agent]` Add a `--dry-run` flag that prints per-file row counts,
  expected API call counts, and category/subcategory assignments without
  hitting the API or writing the DB
- [x] `[agent]` Update `docs/pipeline_plan.md` and any schema/docs/tests that
  still describe the old single-file or flat-category behavior

**Done when**: taxonomy rules are documented; curated CSVs normalize into a
consistent category/subcategory model; one command processes all `poi_nyc/`
files; dry-run shows expected call counts and taxonomy assignments per file.

**User Comments** We should use `data/raw/google_maps/poi_nyc` as the main
source here. For restaurants we've started using `Tags` and `Comment` to
organize into sub-lists. The data model should support `category` and
`subcategory` so Pizza and Ramen can both live under Restaurants while still
being filterable independently. We should make this data-model update first,
then normalize each CSV by assigning taxonomy from the filename and, when
needed, refining subcategory from tags/comments.

---

## WS2 — Run Curated POI Pipeline on All Categories

**Goal**: Get all 15 `poi_nyc/` CSVs resolved and loaded into `dim_user_poi_v2`.

**Depends on**: WS1 complete.

- [ ] `[you]` Run dry-run and review: expected API call count, category
  and subcategory assignment per file, any files that would map to `other`
- [ ] `[you]` Approve API budget and run live
- [ ] `[agent]` Review `dim_user_poi_v2` output: row counts by category and
  subcategory, duplicate place resolutions, any `other` or blank taxonomy rows
  that need reclassification
- [ ] `[you]` Do a manual spot-check of 5-10 resolved places per new category
  to verify Places API matched correctly
- [ ] `[agent]` Update `docs/poi_categories.md` status columns for curated
  categories/subcategories from `raw` → `loaded` with row counts

**Done when**: all `poi_nyc/` source files have `loaded` status in
`poi_categories.md`, taxonomy assignments look clean, and `dim_user_poi_v2`
has clean data.

---

## WS2.5 — Curated POI Canonical Merge Model

**Goal**: Refactor curated POI ingestion so each ingestion path lands in its
own staging table, one canonical curated place row represents one physical
location, and the final merge into `dim_user_poi_v2` preserves source lineage,
match/geo enrichment status, and source-specific metadata without one source
path polluting the others.

**Depends on**: WS2 live run findings reviewed.

- [x] `[you+agent]` Lock the target curated merge design:
  `stg_user_poi_google_takeout`, `stg_user_poi_web_scrape`,
  `stg_user_poi_manual_upload` (or equivalent names) feed a final canonical
  merge into `dim_user_poi_v2`
- [x] `[agent]` Add additive canonical fields to `dim_user_poi_v2` now:
  `category`, `subcategory`, `detail_level_3`, source lineage fields, and geo
  enrichment status fields, while preserving current compatibility columns for
  downstream readers during migration
- [x] `[agent]` Update fallback rules so blank `category` becomes `other` and
  blank `subcategory` falls back to the resolved `category`
- [x] `[agent]` Make the canonical grain explicit: one row per physical
  location / Google Place ID in `dim_user_poi_v2`; multiple source mentions
  survive in source-membership fields or staging tables, not as duplicate place
  rows
- [x] `[agent]` Add a merge policy design for overlap handling:
  `keep_existing` vs `overwrite_with_new_source`, with the WS2.5 default being
  to overwrite legacy curated rows with the new canonical `poi_nyc/` data when
  they refer to the same physical location
- [x] `[agent]` Scope address-aware matching improvements so scraped/manual
  sources can query Google Places with stronger inputs than just
  `title + New York, NY`
- [x] `[agent]` Keep suspicious duplicate place groups in QA outputs for manual
  review even after true-repeat handling improves
- [x] `[agent]` Update docs/tests/schema references so future workstreams build
  on the staged-ingest + canonical-merge model instead of the current
  cache-global shortcut
- [x] `[you]` Review the WS2.5 migration slice before the deeper staging-table
  implementation begins

**Done when**: the target architecture is documented; `dim_user_poi_v2` has the
new additive canonical/source/geo fields; fallback rules match the agreed
behavior; downstream workstreams explicitly depend on the staged merge model;
and the remaining deeper refactor tasks are queued clearly in the downstream
scraping/manual-upload workstreams.

---

## WS3 — Public POI in the Frontend

**Goal**: Surface selected `dim_public_poi` categories as a map layer in
Neighborhood Explorer V2. The table has 27 categories and 56k rows — not all
categories make sense as overlay points and not all rows should load at once.

**Depends on**: WS2.5 canonical field migration complete.

- [ ] `[you]` Decide which categories to expose in the UI. Suggested starting
  set: `subway_station`, `citi_bike_station`, `park`, `grocery_store`,
  `pharmacy`, `public_library`, `farmers_market`. Exclude geometry-only rows
  (`bike_lane`, `subway_line`) and low-signal categories for now.
- [ ] `[you]` Decide UI treatment: same POI layer as curated with a "source"
  filter, or a separate toggleable baseline layer?
- [x] `[agent]` Add `load_public_poi_map_data()` to `base_map.py` that loads
  only the selected categories from `dim_public_poi`
- [x] `[agent]` Add the public POI layer and filter controls to
  `streamlit_app_v2.py`
- [x] `[you]` Review in the app: does it load fast enough? Do the right places
  show up? Is the filter UI clear?
- [x] `[agent]` Fix any performance or UI issues from review

**Done when**: selected public POI categories are toggleable on the map and
load in reasonable time.

**User decisions locked on 2026-04-28**
- Public categories to expose in WS3: `atm`, `bank`, `citi_bike_station`,
  `dog_run`, `farmers_market`, `ferry_terminal`, `grocery_store`, `gym`,
  `hospital`, `landmark`, `museum_institutional` (requested in UI language as
  "museum_institution"), `park`, `path_station`, `pharmacy`, `post_office`,
  `public_art`, `public_library`, `subway_station`, `urgent_care`
- UI treatment: curated and public POIs should be separate map layers with
  independent toggles
- First-load UX refinement on 2026-04-28: default to curated POIs only, keep
  public POIs off until toggled on, and start the public category selection at
  `subway_station`

---

## WS4 — Neighborhood Explorer Full Review

**Goal**: Review the app end-to-end after WS2 and WS3 are done. Use
`docs/neighborhood_explorer_app_review.md` as the checklist baseline.

**Depends on**: WS2.5 + WS3 complete.

- [x] `[you]` Open the app and walk through the core workflow: browse
  neighborhoods, toggle POI categories (curated + public), select a tract/NTA,
  review demographic context
- [x] `[you]` Note anything broken, confusing, or missing
- [x] `[you+agent]` Prioritize fixes from the review session
- [x] `[agent]` Implement agreed fixes

**Done when**: you can do a full demo walkthrough without hitting anything broken
or obviously misleading.

**Completion notes**
- First live review on 2026-04-28 confirmed the core neighborhood workflow was
  usable after WS3 landed: curated/public layer toggles, neighborhood-first
  demographic view, and five-borough geography now render without obvious
  breakage
- Follow-up fixes from that review moved into WS4.5 and are now implemented

**Follow-up items from first live app review on 2026-04-28**
- [ ] `[agent]` Add `population` and `population_growth_3yr` to the tract/NTA
  feature model, pipeline, QA checks, and Neighborhood Explorer metric picker
  once those fields are sourced and validated
- [ ] `[agent]` Add broader public POI rollups for tooltip/display use
  (future buckets such as Shopping, Culture, Food) so raw category counts can
  collapse into higher-level summaries
- [ ] `[agent]` Review Neighborhood Explorer load time and trim avoidable first-
  paint latency after the tooltip/count UX settles
- [ ] `[agent]` Reduce neighborhood/tract tooltip size or make tooltip content
  scroll/compact so long hover cards do not get cut off on smaller screens

---

## WS4.5 — NTA Feature + Frontend Refinement

**Goal**: Clean up the neighborhood-first app experience after the first live
WS4 review, with a focus on the `fct_nta_features` model, tooltip polish, and
load-time optimization.

**Depends on**: WS4 first review complete.

- [x] `[agent]` Refactor `fct_nta_features` so neighborhood-level app views can
  rely on a stronger NTA-native metric contract instead of only inheriting the
  current tract-first summary shape
- [x] `[agent]` Remove the misleading `Tract: Unavailable` line from
  neighborhood tooltips while keeping tract IDs visible in tract mode
- [x] `[agent]` Do a focused frontend performance pass to reduce first-load
  latency in Neighborhood Explorer
- [x] `[agent]` Re-check map-layer ordering and tooltip interaction after the
  NTA feature refactor/performance changes land

**Done when**: neighborhood tooltips are clean, the NTA feature layer is on a
clearer footing, and first-load performance has improved materially.

**Completion notes**
- `fct_nta_features` now carries a stronger NTA-native contract with
  `borough` and `tract_count`, while remaining one row per `nta_id`
- Neighborhood tooltips no longer show `Tract: Unavailable`; tract IDs remain
  visible in tract mode
- Public POIs are lazy-loaded behind the toggle, with `subway_station` as the
  default first selection
- Timing snapshot on 2026-04-28 after the refactor:
  `load_base_geography_data` ≈ `1.37s`
  `build_base_map_data_from_loaded(...)` ≈ `0.04s` per metric switch
  `load_poi_map_data` ≈ `0.07s`
  `load_public_poi_map_data(subway_station)` ≈ `0.06s`
- Remaining perceived load is now more likely dominated by Streamlit render and
  browser-side map draw cost than by repeated backend data prep

---

## WS5 — QA App: Add POI Coverage Panels

**Goal**: Bring the QA app in line with the POI and frontend work already
completed through WS4.5 so it covers POI data quality, canonical curated
taxonomy visibility, public inventory gaps, and pipeline freshness alongside
demographic coverage.

**Depends on**: WS2.5 (curated POI canonical merge slice landed).

- [x] `[agent]` Add a `dim_user_poi_v2` panel: row counts by category,
  unresolved/`other` rows, duplicate Place IDs flagged for review
- [x] `[agent]` Upgrade the curated POI panel to show the full configured
  category + subcategory inventory from WS1/WS2.5 so missing expected taxonomy
  rows are visible directly
- [x] `[agent]` Add a `dim_public_poi` panel: row counts by category vs.
  expected baseline counts, any categories with zero rows
- [x] `[agent]` Upgrade table readiness so the QA app also reports curated/public
  POI tables and staged curated POI tables introduced by WS2.5
- [x] `[agent]` Add a pipeline freshness panel covering DB-level freshness plus
  curated/public POI timestamp signals and curated cache timestamps
- [ ] `[you]` Review QA app output and confirm data looks clean before WS4

**Done when**: QA app shows POI coverage and you've signed off on data quality.

**User decision locked on 2026-04-28**
- QA should list the full curated and public category inventories, not just
  categories present in the tables, so missing categories are visible directly

**Completion notes**
- The QA app now reports curated/public POI coverage alongside demographic
  coverage instead of treating POIs as an add-on
- Curated QA now follows the WS1 taxonomy contract at `category` +
  `subcategory` grain and shows configured inventory rows even when missing
- Public QA still shows the full expected category inventory, highlights WS3 UI
  gaps, and includes source-system visibility per category
- Gold-table readiness now includes `dim_user_poi_v2`, `dim_public_poi`, and
  the WS2.5 curated staging tables
- Freshness reporting now includes DuckDB mtime, curated/public table timestamps,
  and curated cache mtimes to make rerun/debug decisions easier

**Execution-order note**
- WS5 landed after WS3/WS4 in practice. The QA app has now been backfilled so
  it reflects the current post-WS4.5 state even though the original intended
  order was WS5 before the main app review

---

## WS6 — Curated POI Expansion: Scraping

**Goal**: Add a scraping path for extracting places from editorial articles
(Eater, Time Out, and semi-manual sources) into `dim_user_poi_v2`. Fully
manual-seed inputs (Permanent Style, Substack Mismatch, Backseat Driver) are
handled in WS7, not here.

**Depends on**: WS2.5 complete.

**Implementation note locked on 2026-04-28**: Any app-facing curated POI
grouping/filtering should key off the latest canonical curated `category`
field, not source filenames or raw saved-list names.

**State as of 2026-04-28**: The upstream half of this workstream is done.
The scraper scaffold, Eater parser, config-backed article registry, normalized
CSV contract, and CLI entry point are all built and tested. 17 articles across
8 publishers are registered in `config/curated_scrape_articles.yaml` with
locked taxonomy. The downstream half — resolve adapter, staging writer, and
canonical merge — is the remaining implementation work. No live article HTML
has been processed yet.

### Already done

- [x] `[you+agent]` Design scraper module structure, output schema, and article
  registry (`curated_poi/web_scraping/`, `config/curated_scrape_articles.yaml`)
- [x] `[agent]` Implement normalized CSV contract: `ScrapedArticleRow`,
  `NormalizedScrapedRow`, `normalize_article_rows`, multi-address splitter,
  `search_query` builder, stable `source_record_id`
- [x] `[agent]` Implement config-backed article registry with `get_article()`,
  `list_articles()`, and locked article taxonomy for all 17 registered articles
- [x] `[agent]` Implement Eater parser: JSON-LD `ItemList` extraction, section-
  text address/description extraction, multi-address row expansion
- [x] `[agent]` Implement `export_curated_poi_eater_article` CLI: `--list-articles`,
  `--article-slug`, `--html`, `--url`

### Phase 1 — First end-to-end Eater article

- [ ] `[you]` Save one real Eater HTML file locally under
  `data/raw/scraped/raw/eater/<slug>_<date>.html` and run the parser; review
  normalized CSV for address coverage, multi-address splits, and taxonomy before
  any resolve work begins
- [ ] `[agent]` Build web-scrape resolve adapter: reads a normalized scrape CSV,
  maps `search_query` / `input_title` into the Places text search flow, reuses
  the existing resolve and enrich machinery from `curated_poi/google_takeout/`
  via a new `curated_poi/shared/` module rather than duplicating it
- [ ] `[agent]` Write `stg_user_poi_web_scrape` writer and canonical merge path
  into `dim_user_poi_v2` following the same staged-ingest model as
  `stg_user_poi_google_takeout`
- [ ] `[agent]` Make the export CLI generic: a new
  `export_curated_poi_article` entry point that routes by `parser_name` from
  the registry; keep `export_curated_poi_eater_article` as a compatibility alias
- [ ] `[you]` Run first Eater article end to end; spot-check resolved rows in
  `dim_user_poi_v2` and advance article status to `loaded` in config

### Phase 2 — Remaining Eater articles

- [ ] `[you]` Save HTML files for the remaining 4 Eater articles and run the
  parser on each; review normalized CSVs before resolve
- [ ] `[you]` Run remaining Eater articles through resolve/stage/merge; advance
  each to `loaded` in `config/curated_scrape_articles.yaml`

### Phase 3 — Time Out parser

- [ ] `[agent]` Build Time Out parser (`publications/timeout.py`); Time Out
  article structure differs from Eater so this needs its own parser class under
  the same `ScrapedArticleRow` contract
- [ ] `[you]` Save Time Out HTML files for the 3 registered articles and run the
  parser; review normalized CSVs
- [ ] `[you]` Run Time Out articles through resolve/stage/merge; advance each to
  `loaded` in config

### Phase 4 — Semi-manual sources

Semi-manual articles (Wanderlog, Michelin Guide, Bon Appetit, NY Mag) use
`capture_mode: semi_manual` and do not need a dedicated publication parser.

- [ ] `[agent]` Build the semi-manual normalization path: reads a saved HTML or
  text extract, applies a lightweight generic extractor or LLM-assisted pass,
  writes the same normalized CSV contract
- [ ] `[you]` Process the 4 semi-manual articles one at a time: capture raw
  content locally, run normalization, review CSV, run through resolve/stage/merge,
  advance to `loaded` in config

**Done when**: all 5 Eater articles, all 3 Time Out articles, and all 4
semi-manual articles show `loaded` status in `config/curated_scrape_articles.yaml`
and their rows are visible in `dim_user_poi_v2`.

---

## WS7 — Curated POI Expansion: Public Excel / Crowd Submissions

**Goal**: Allow others (or yourself) to submit places via a shared
Excel/CSV template that flows into `dim_user_poi_v2`.

**Depends on**: WS2.5 complete.

- [ ] `[you]` Define the template fields: at minimum name, address (optional),
  URL, category, submitter notes
- [ ] `[you+agent]` Design the normalization pipeline (reads the template →
  normalizes → routes to Places API resolve step → lands in the manual-upload
  staging table before canonical merge)
- [ ] `[agent]` Implement the template reader and normalization module
- [ ] `[agent]` Implement the manual-upload staging writer and canonical merge
  promotion path for contributor-submitted curated POIs
- [ ] `[agent]` Document the submission workflow in `docs/poi_categories.md`

**Done when**: a filled template CSV can be processed end-to-end into
`dim_user_poi_v2`.

---

## WS8 — Intelligence Layer

**Goal**: Add analysis and scoring surfaces that help answer "which neighborhood
is best for me?" rather than just displaying raw data.

**Depends on**: WS2.5 + WS3 + WS4 (app must have all POIs loaded and reviewed
before building analysis on top of them).

Before any implementation, agree on what questions to answer:

- [ ] `[you]` Decide the primary question: neighborhood POI density ranking?
  personal fit score redesign? "best NTA for your preferences" summary card?
- [ ] `[you+agent]` Write a one-page scoring design doc (inputs, weights,
  missing-data behavior) — do not build before this exists
- [ ] `[agent]` Update `fct_property_context` to also use `dim_public_poi`
  for proximity counts (parks, subway stations, grocery stores)
- [ ] `[agent]` Add a neighborhood summary panel to the app (top NTAs by
  selected POI density + demographic context)
- [ ] `[you]` Review scoring results against your intuition for known neighborhoods

**Done when**: the app surfaces at least one analysis view that helps you make
a neighborhood decision, not just browse data.

---

## Execution Order

```
WS1  →  WS2  →  WS2.5  →  WS5  →  WS3  →  WS4
                                        ↓
                                   WS6, WS7
                                        ↓
                                       WS8
```

Do WS1 and WS2 first to prove the batch pipeline and capture live-run findings.
Then do WS2.5 before more feature work so curated POIs have the right canonical
merge model, source lineage, and matching contract. Run WS5 (QA) before WS4
(app review) so you can trust what you're reviewing. WS6 and WS7 can run in
parallel after WS2.5 once the staged-ingest + canonical-merge model is stable.
WS8 last — it needs all POI data in the app before analysis is credible.

Real Estate Listings are intentionally out of scope until further notice.
