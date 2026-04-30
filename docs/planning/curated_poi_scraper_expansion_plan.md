# Curated POI Scraper Expansion Plan

Last updated: 2026-04-28

This doc is the working plan for expanding curated POI scraping beyond the
first Eater slice. It explains the current implementation, how article sources
should be evaluated, and the end-to-end path from article discovery to loaded
rows in `dim_user_poi_v2`.

Use this doc when deciding:

- which publication families are worth parser investment
- how a new article should be added to the scrape inventory
- where scraped data lives before it reaches DuckDB
- what implementation gaps still remain between normalized scrape CSVs and the
  final canonical curated POI table

---

## Current State

Last updated: 2026-04-28

The upstream half of the scraper system is complete. The downstream pipeline
is the remaining work.

### Implemented

- **Article registry**: 17 articles across 8 publishers registered in
  `config/curated_scrape_articles.yaml` with locked article-level taxonomy
  (`category`, `subcategory`, `detail_level_3`, `capture_mode`, `parser_name`)
- **Runtime registry loader**: `web_scraping/registry.py` with `get_article()`,
  `list_articles()`, and `lru_cache`-backed config loading
- **Normalized scrape contract**: `ScrapedArticleConfig`, `ScrapedArticleRow`,
  `NormalizedScrapedRow` in `web_scraping/base.py`; includes multi-address
  splitter, `search_query` builder, and stable `source_record_id`
- **Eater parser**: `web_scraping/publications/eater.py` — custom `HTMLParser`
  subclass; extracts JSON-LD `ItemList` items, matches section text by heading
  id/slug, pulls address via `"Location..."` pattern and description via
  `"Why we love it..."` pattern, expands multi-address rows
- **Normalization helpers**: `web_scraping/normalize.py` — DataFrame builder
  and CSV writer
- **CLI entry point**: `pipelines/export_curated_poi_eater_article.py` with
  `--list-articles`, `--article-slug`, `--html`, `--url`, `--out`
- **Tests**: registry, parser, normalization, and output path naming all covered

No live article HTML has been processed yet.

### Not implemented

- Generic normalized-scrape-to-Places resolve adapter
- Writer for `property_explorer_gold.stg_user_poi_web_scrape`
- Canonical merge from web-scrape stage into `dim_user_poi_v2`
- Generic export CLI that routes by `parser_name` (current CLI is Eater-specific)
- Time Out parser (`publications/timeout.py`)
- Semi-manual normalization path for `capture_mode: semi_manual` articles
- `curated_poi/shared/` module for resolve/enrich logic shared across source paths

The current pipeline boundary is:

```text
article config
  -> raw article capture
  -> publication-specific parser
  -> normalized CSV for QA          ← current boundary
```

The target is:

```text
article config
  -> raw article capture
  -> publication-specific parser
  -> normalized CSV for QA
  -> Places resolution + details enrichment   ← next to build
  -> stg_user_poi_web_scrape
  -> dim_user_poi_v2
```

---

## Current Implementation

### Inventory and registry

- Config source of truth: `config/curated_scrape_articles.yaml`
- Runtime registry loader: `src/nyc_property_finder/curated_poi/web_scraping/registry.py`

Current config fields:

- `publisher`
- `article_slug`
- `article_title`
- `article_url`
- `source_list_name`
- `category`
- `subcategory`
- `detail_level_3`
- `capture_mode`
- `parser_name`
- `status`

These fields are intentionally lean. They support:

- inventory management
- article-level taxonomy locking
- routing into parser vs. semi-manual vs. manual workflows
- lightweight history as articles move through the pipeline

### Package shape

Current scraper package layout:

```text
src/nyc_property_finder/curated_poi/web_scraping/
  base.py
  normalize.py
  registry.py
  publications/
    eater.py
```

### Current Eater workflow

Current CLI entry point:

`nyc_property_finder.pipelines.export_curated_poi_eater_article`

What it does today:

- lists registered Eater articles from config
- reads a local saved HTML file or fetches a live URL
- parses Eater JSON-LD and nearby section text
- extracts ranked place rows
- splits multi-address rows
- writes one normalized review CSV

This is a file-first workflow by design. Nothing from scraping goes straight to
DuckDB yet.

---

## Source Strategy

Not every source deserves a dedicated parser. The scraper program should
separate publication families from one-off articles.

### Best publication-family candidates

These are the sources most likely to justify reusable parser investment:

1. `Eater`
2. `Time Out`
3. `Vogue`

Why:

- multiple relevant NYC articles already identified
- recurring editorial structure
- high chance of parser reuse across several articles

### Better as semi-manual or one-off

These sources are still useful, but less likely to justify a robust parser
early:

- `Michelin Guide`
- `Wanderlog`
- `Bon Appetit`
- `NY Mag`
- `Permanent Style`
- `Substack Mismatch`
- `Backseat Driver`

These should usually start as:

- `semi_manual` when a saved HTML or text extract is enough
- `manual_seed` when the article count is low and the effort to automate is not worth it

### Practical parser investment order

Recommended build order:

1. Eater
2. Time Out
3. Vogue
4. generic semi-manual normalization helpers
5. reevaluate whether any additional publication deserves a dedicated parser

---

## Capture Modes

Every article in `config/curated_scrape_articles.yaml` should declare one of
these modes:

### `parser`

Use when a publication has enough repeated structure to justify dedicated code.

Examples:

- Eater
- likely Time Out
- likely Vogue

### `semi_manual`

Use when we want to save the source HTML or text locally and run a lighter
normalization pass without a fully developed publication parser.

Examples:

- Michelin Guide
- Wanderlog
- Bon Appetit
- NY Mag

### `manual_seed`

Use when the volume is low or the source structure is awkward enough that a
hand-built normalized CSV is the simplest reliable path.

Examples:

- Permanent Style
- Substack Mismatch
- Backseat Driver

---

## Normalized Row Contract

All scraping paths should converge on the same reviewable normalized contract
before Places resolution.

Minimum normalized fields:

- `publisher`
- `article_title`
- `article_url`
- `source_list_name`
- `item_rank`
- `item_name`
- `item_url`
- `raw_address`
- `raw_description`
- `raw_neighborhood`
- `raw_borough`
- `category`
- `subcategory`
- `detail_level_3`
- `scraped_at`

Fields used to align with the downstream curated resolve contract:

- `input_title` = `item_name`
- `note` = `raw_address`
- `comment` = `raw_description`
- `source_url` = `article_url` or `item_url`
- `search_query` = `item_name + raw_address + New York, NY`

### Pre-resolution grain

The pre-resolution source row should represent one physical location candidate.

That means:

- one venue with one address = one source row
- one venue with three addresses = three source rows

This is important for chains and multi-location editorial mentions.

---

## Taxonomy Rules For Scraped Articles

Article-level taxonomy should be locked before parser work begins.

Recommended precedence:

1. article or list identity
2. publication-specific parser hints
3. description keyword extraction
4. Google Places metadata after resolution for enrichment only

Important principle:

- do not let Google Places become the primary taxonomy source for scraped lists

The scraper should emit the intended curated taxonomy up front. Places is mainly
for location matching, canonical address normalization, and coordinates.

---

## End-To-End Flow

This is the target operational path for one scraped article.

### 1. Identify the article

Choose a candidate source and decide:

- is it worth a dedicated parser?
- is it better as `semi_manual`?
- is it better as `manual_seed`?

### 2. Add the article to config

Add a new row to `config/curated_scrape_articles.yaml` with:

- article identity
- URL
- source list name
- taxonomy
- capture mode
- parser name
- initial status

Recommended first statuses:

- `planned`
- `registered`

### 3. Capture raw article content

Save raw HTML or text locally:

```text
data/raw/scraped/raw/<publication>/<slug>_<date>.html
data/raw/scraped/raw/<publication>/<slug>_<date>.txt
```

Why file-first:

- reproducible QA
- easier reruns
- easier debugging
- manual fallback stays compatible with the same workflow

### 4. Parse or normalize the article

If the article uses an existing parser family:

- run the publication-specific export CLI or helper

If not:

- build a new parser under `web_scraping/publications/`
- or use a lighter semi-manual normalization path

### 5. Write the normalized review CSV

Write output to:

```text
data/raw/scraped/normalized/<category>_<publication>_<slug>_<date>.csv
```

At this stage, the file is still review-first rather than DB-first.

### 6. QA the normalized output

Before Places resolution, review:

- row count
- missing names
- missing addresses
- duplicate `item_name + raw_address`
- multi-address rows split correctly
- obvious non-place rows removed
- taxonomy correctness

Recommended next statuses:

- `captured`
- `normalized`

### 7. Resolve with Google Places

This is the next major implementation gap.

We need a web-scrape ingestion path that:

- reads normalized scrape CSVs
- maps them into the same pre-resolution contract used by other curated paths
- resolves each row via Places text search
- enriches unique `google_place_id` rows with Place Details

Expected outputs from this stage:

- canonical address
- `google_place_id`
- `lat`
- `lon`
- match status

Recommended next status:

- `resolved`

### 8. Write to `stg_user_poi_web_scrape`

Once web-scrape resolution is wired in, resolved rows should land in:

`property_explorer_gold.stg_user_poi_web_scrape`

This table should preserve source-specific metadata and lineage in the same
spirit as the Google Takeout stage.

### 9. Merge into `dim_user_poi_v2`

Canonical merge should follow the existing curated POI grain:

- one row per physical location / Google Place ID

Important rules:

- multiple source mentions of the same place should not create duplicate final rows
- source lineage should survive
- canonical `category` and `subcategory` should remain explicit

Recommended final status:

- `loaded`

---

## Implementation Gaps

The remaining gaps, in priority order:

1. **Web-scrape resolve adapter** — reads a normalized scrape CSV, maps
   `search_query` / `input_title` into the Places text search flow; should
   reuse resolve and enrich logic from `curated_poi/google_takeout/` via a new
   `curated_poi/shared/` module rather than duplicating it
2. **`stg_user_poi_web_scrape` writer** — same staged-ingest model as
   `stg_user_poi_google_takeout`
3. **Canonical merge integration** — promote from web-scrape stage into
   `dim_user_poi_v2`, following existing merge policy
4. **Generic export CLI** — `export_curated_poi_article` that routes by
   `parser_name`; keeps Eater CLI as compatibility alias
5. **Time Out parser** — `publications/timeout.py` under the same contract
6. **Semi-manual normalization path** — lightweight extractor or LLM-assisted
   pass for `capture_mode: semi_manual` articles

---

## Suggested Status Lifecycle

- `planned`: article identified but not yet locked in the active queue
- `registered`: article added to config with locked taxonomy
- `captured`: raw HTML or text saved locally
- `normalized`: review CSV produced and accepted
- `resolved`: Places resolution and details enrichment completed
- `loaded`: staged and merged into `dim_user_poi_v2`

---

## Recommended Next Steps

1. Save one real Eater article HTML locally and run the parser. Review the
   normalized CSV — particularly address coverage — before building the resolve
   path.
2. Build the resolve adapter + stage writer + canonical merge (the whole
   downstream pipe in one pass since the pieces are small).
3. Run first Eater article end to end. Confirm rows appear in `dim_user_poi_v2`.
4. Process remaining 4 Eater articles.
5. Build Time Out parser and run its 3 articles.
6. Build semi-manual normalization path and process 4 semi-manual articles.

Do not build more parser coverage before the downstream ingestion path exists.
