# Google Places Enrichment Expansion

Last updated: 2026-04-29
Status: completed and archived

## Goal

Expand curated Google Places enrichment so both Google Takeout and web-scrape
pipelines carry richer Place Details metadata into `dim_user_poi_v2`.

## What Shipped

The final implementation shipped a slightly stronger version than the original
plan:

- The default Place Details field mask now requests:
  `displayName`, `formattedAddress`, `location`, `rating`,
  `userRatingCount`, `businessStatus`, `editorialSummary`, `priceLevel`, and
  `websiteUri`
- `dim_user_poi_v2` and the curated staging tables now surface 7 new columns:
  `rating`, `user_rating_count`, `business_status`, `editorial_summary`,
  `editorial_summary_language_code`, `price_level`, and `website_uri`
- Missing string-like values are stored as nulls instead of empty strings
- Raw Google enum values are preserved as returned
- The shared Place Details cache now stores `field_mask` and
  `cache_schema_version` metadata so future enrichment changes can selectively
  refresh stale rows instead of requiring a full cache wipe
- The refresh was applied across all place IDs in the shared resolution cache,
  not only the Google Takeout slice
- Both Google Takeout and web-scrape ingestion paths now carry these fields all
  the way through to `dim_user_poi_v2`

## Final Warehouse Columns

| Column | Source API key | Notes |
| --- | --- | --- |
| `rating` | `rating` | Nullable float |
| `user_rating_count` | `userRatingCount` | Nullable pandas `Int64` during build |
| `business_status` | `businessStatus` | Raw Google enum |
| `editorial_summary` | `editorialSummary.text` | Nullable text |
| `editorial_summary_language_code` | `editorialSummary.languageCode` | Nullable language code |
| `price_level` | `priceLevel` | Raw Google enum |
| `website_uri` | `websiteUri` | Nullable URL |

## Relevant Files

| File | Role |
| --- | --- |
| `src/nyc_property_finder/curated_poi/google_takeout/client.py` | Canonical Place Details field mask |
| `src/nyc_property_finder/curated_poi/google_takeout/cache.py` | Shared details-cache metadata and current-version checks |
| `src/nyc_property_finder/curated_poi/google_takeout/enrich.py` | Selective refresh of missing or stale cached details rows |
| `src/nyc_property_finder/curated_poi/google_takeout/build_dim.py` | Extraction and coercion into curated warehouse columns |
| `sql/ddl/001_gold_tables.sql` | Curated dim/staging DDL |
| `docs/data_model.md` | Current `dim_user_poi_v2` contract |
| `tests/test_google_places_poi.py` and `tests/test_schema.py` | Regression coverage |

## Completion Notes

- Local curated DuckDB tables were dropped and recreated so the new columns
  existed in `dim_user_poi_v2`, `stg_user_poi_google_takeout`,
  `stg_user_poi_web_scrape`, and `stg_user_poi_manual_upload`
- The shared details cache was refreshed to the new versioned payload shape
- The Google Takeout batch was rebuilt successfully
- Normalized web-scrape inputs were replayed successfully with `0` new Text
  Search calls and `0` new Place Details calls after the cache refresh
- Spot checks confirmed the new fields were populated for well-known venues

## Final Validation Snapshot

As of the completion run on 2026-04-29:

- shared resolved place IDs with current details rows: `543`
- stale latest-version details rows remaining: `0`
- canonical curated rows in `dim_user_poi_v2`: `525`
- Takeout stage rows: `386`
- Web-scrape stage rows: `158`

## Definition of Done

- [x] `PLACE_DETAILS_FIELD_MASK` expanded to the richer default field set
- [x] `DIM_USER_POI_V2_COLUMNS` expanded to include the shipped warehouse fields
- [x] Build logic extracts and coerces the new fields from cached payloads
- [x] Curated DDL updated for staged and canonical curated POI tables
- [x] `docs/data_model.md` documents the new columns
- [x] Local curated DuckDB tables recreated with the new schema
- [x] Shared Place Details cache refreshed to the current versioned payload shape
- [x] Google Takeout and web-scrape pipelines both rebuild into `dim_user_poi_v2`
