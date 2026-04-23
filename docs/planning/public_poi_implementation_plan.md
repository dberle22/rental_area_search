# Public POI Implementation Plan

Planning date: 2026-04-23  
Scope: Table 1 of `poi_category_expansion.md` — baseline public data only.  
Decisions locked in: `dim_public_poi` is its own table; snapshots (not live re-query) are the ingestion model; Google Places Nearby Search fallbacks are deferred.

---

## To-Do Checklist

Work top to bottom. Each group maps to a section of this document.

### Foundation

- [x] Write `sql/ddl/002_public_poi_table.sql` with the `dim_public_poi` DDL
- [x] Run `init_database` to create the table in DuckDB
- [x] Scaffold `src/nyc_property_finder/public_poi/` — `__init__.py`, `config.py`, `build_dim.py`, `pipeline.py`
- [x] Scaffold `src/nyc_property_finder/public_poi/sources/` — `__init__.py` only, empty stubs for each module
- [x] Create `src/nyc_property_finder/pipelines/ingest_public_poi.py` entry point shell (imports `run`, no logic yet)
- [x] Create `data/raw/public_poi/` directory tree (subdirs per source)

### Wave 1 — Transit

- [x] `sources/mta_subway.py` — `load()` for subway stations (`location_type=1`) from existing `data/raw/transit/gtfs_subway.zip`
- [x] `sources/mta_subway.py` — `load()` for subway entrances (`location_type=2`)
- [x] `sources/mta_subway.py` — `load()` for subway line geometry (centroids from `shapes.txt`)
- [x] `sources/mta_bus.py` — `fetch_snapshot()` for all 5 borough GTFS feeds
- [x] `sources/mta_bus.py` — `load()` unioning all 5 `stops.txt` files, deduped on `stop_id`
- [x] `sources/gbfs_citibike.py` — `fetch_snapshot()` from GBFS JSON endpoint
- [x] `sources/gbfs_citibike.py` — `load()` parsing station list
- [x] Create hand-entry CSV `data/raw/public_poi/ferry_path/terminals.csv` with 9 Ferry terminals + ~12 PATH stops
- [x] `sources/ferry_path.py` — `load()` reading the hand-entry CSV (no `fetch_snapshot` needed)
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for bike lanes (Socrata `s6d2-j7cd`)
- [x] Wire Wave 1 sources into `build_dim.py` + `pipeline.py`; run end-to-end and verify row counts in DuckDB

Wave 1 verification: pipeline run on 2026-04-23 wrote 43,682 rows to
`property_explorer_gold.dim_public_poi`, all with coordinates. Current category
counts: `bike_lane` 28,983; `bus_stop` 11,523; `citi_bike_station` 2,406;
`subway_station` 496; `subway_line` 252; `ferry_terminal` 9; `path_station` 13.
The current MTA subway GTFS snapshot contains no `location_type=2` entrance rows,
but the loader handles them when present. The current NYC Bike Routes Socrata
dataset is exposed as `mzxg-pwib`; the original planning ID returned 404 during
implementation.

### Wave 2 — Parks & Recreation

- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for parks (Socrata `enfh-gkve`); derive centroid from polygon, apply `typecategory` filter
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for dog runs (Socrata `hxx3-bwgv`)
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for playgrounds (Socrata `j55h-3upk`)
- [x] Add Wave 2 sources to `pipeline.py`; re-run and verify

Wave 2 verification: pipeline run on 2026-04-23 wrote 46,061 rows to
`property_explorer_gold.dim_public_poi`, all with coordinates. Wave 2 category
counts: `park` 1,276; `playground` 1,011; `dog_run` 92. Current full category
counts: `bike_lane` 28,983; `bus_stop` 11,523; `citi_bike_station` 2,406;
`park` 1,276; `playground` 1,011; `subway_station` 496; `subway_line` 252;
`dog_run` 92; `path_station` 13; `ferry_terminal` 9. The originally planned
dog-run and playground Socrata IDs were stale; implementation uses current NYC
Open Data datasets `hxx3-bwgv` (Dog Runs) and `j55h-3upk` (Children's Play
Areas / playgrounds). NYC Parks properties still use `enfh-gkve`, filtered to
the planned recreational `typecategory` allowlist.

### Wave 3 — Everyday Retail Baseline

- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for grocery stores (Socrata `9w7m-hzhe`); filter to supermarkets
- [x] `sources/nyc_open_data.py` — `load()` for laundromats from DCWP dataset (Socrata `w7w3-xahh`; industry code 110)
- [x] `sources/nyc_open_data.py` — `load()` for dry cleaners from same DCWP dataset (industry code 113)
- [x] `sources/osm.py` — `fetch_snapshot()` + `load()` for pharmacies (`amenity=pharmacy`)
- [x] `sources/osm.py` — `fetch_snapshot()` + `load()` for banks (`amenity=bank`)
- [x] `sources/osm.py` — `fetch_snapshot()` + `load()` for ATMs (`amenity=atm`)
- [x] `sources/osm.py` — `fetch_snapshot()` + `load()` for hardware stores (`shop=hardware`)
- [x] Add Wave 3 sources to `pipeline.py`; re-run and verify

Wave 3 verification: pipeline run on 2026-04-23 wrote 50,695 rows to
`property_explorer_gold.dim_public_poi`, all with coordinates. Wave 3 category
counts: `bank` 1,465; `grocery_store` 1,315; `pharmacy` 1,258; `atm` 342;
`hardware_store` 241; `dry_cleaner` 7; `laundromat` 6. Current full category
counts: `bike_lane` 28,983; `bus_stop` 11,523; `citi_bike_station` 2,406;
`bank` 1,465; `grocery_store` 1,315; `park` 1,276; `pharmacy` 1,258;
`playground` 1,011; `subway_station` 496; `atm` 342; `subway_line` 252;
`hardware_store` 241; `dog_run` 92; `path_station` 13; `ferry_terminal` 9;
`dry_cleaner` 7; `laundromat` 6. The originally planned grocery Socrata ID
`9w7m-hzhe` currently resolves to restaurant inspections, so implementation
uses the current NYS Department of Agriculture and Markets retail food stores
dataset `9a8c-vfzj`, filtered to NYC supermarket-style rows. The current DCWP
`w7w3-xahh` schema no longer exposes the planned industry-code columns, so the
laundromat and dry-cleaner loaders support those legacy codes when present and
use the live `business_category` plus business-name filters for today's
snapshot. Current DCWP coverage for neighborhood laundromats/dry cleaners is
sparse and should be revisited if those categories become scoring-critical.

### Wave 4 — Civic & Community

- [x] `sources/nypl_api.py` — `fetch_snapshot()` + `load()` for NYPL branches (Refinery API, no key)
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for BPL branches (Socrata `ukuu-ndnd` or hand-entry CSV)
- [x] Create hand-entry CSV for Queens Public Library branches; add `load()` in `nyc_open_data.py`
- [x] Merge all three library sources into `category="public_library"` with `subcategory` = `nypl | bpl | qpl`
- [x] `sources/osm.py` — `fetch_snapshot()` + `load()` for post offices (`amenity=post_office`)
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for public schools (Socrata `r2nx-nhxe`)
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for farmers markets (Socrata `8vwk-6iz2`)
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for hospitals (Socrata `833h-xwsx`); filter to open general hospitals
- [x] `sources/osm.py` — `fetch_snapshot()` + `load()` for urgent care (`amenity=clinic`); note: manual curation pass needed after first ingest
- [x] `sources/osm.py` — `fetch_snapshot()` + `load()` for gyms (`leisure=fitness_centre`)
- [x] Add Wave 4 sources to `pipeline.py`; re-run and verify

Wave 4 verification: pipeline run on 2026-04-23 wrote 54,623 rows to
`property_explorer_gold.dim_public_poi`, all with coordinates. Wave 4 category
counts: `public_school` 1,595; `gym` 771; `urgent_care` 731; `post_office`
417; `public_library` 214; `farmers_market` 127; `hospital` 73. Library
subcategories are `nypl` 93, `qpl` 62, and `bpl` 59. Hospital rows come from
the current DCP Facilities Database and include `HOSPITAL` 62 plus
`ACUTE CARE HOSPITAL` 11. Current full category counts: `bike_lane` 28,983;
`bus_stop` 11,523; `citi_bike_station` 2,406; `public_school` 1,595; `bank`
1,465; `grocery_store` 1,315; `park` 1,276; `pharmacy` 1,258; `playground`
1,011; `gym` 771; `urgent_care` 731; `subway_station` 496; `post_office` 417;
`atm` 342; `subway_line` 252; `hardware_store` 241; `public_library` 214;
`farmers_market` 127; `dog_run` 92; `hospital` 73; `path_station` 13;
`ferry_terminal` 9; `dry_cleaner` 7; `laundromat` 6. The originally planned
BPL and hospital Socrata IDs (`ukuu-ndnd` and `833h-xwsx`) currently return
404s; implementation uses the current NYC Open Data `LIBRARY` dataset
(`feuq-due4`) for BPL rows and DCP Facilities Database (`ji82-xba5`) for
hospital rows. Queens Public Library rows are stored in the requested static
CSV from the current Queens Library Branches dataset (`kh3d-xhq7`).

### Wave 5 — Culture & Heritage

- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for individual landmarks (Socrata `s4sh-z6gg`)
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for historic districts (Socrata `xbvj-gfnw`); derive centroid
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for DCLA institutional museums
- [x] `sources/nyc_open_data.py` — `fetch_snapshot()` + `load()` for public art / Art in the Parks (Socrata `zbs8-ab7x`)
- [x] Add Wave 5 sources to `pipeline.py`; re-run and verify

Wave 5 verification: pipeline run on 2026-04-23 wrote 57,129 rows to
`property_explorer_gold.dim_public_poi`, all with coordinates. Wave 5 category
counts: `landmark` 1,629; `public_art` 775; `museum_institutional` 102.
Landmark rows include `Individual Landmark` 1,472 and `historic_district` 157.
DCLA museum subcategories are `museum` 85, `science` 9, `botanical` 5, and
`zoo` 3. Current full category counts: `bike_lane` 28,983; `bus_stop` 11,523;
`citi_bike_station` 2,406; `landmark` 1,629; `public_school` 1,595; `bank`
1,465; `grocery_store` 1,315; `park` 1,276; `pharmacy` 1,258; `playground`
1,011; `public_art` 775; `gym` 771; `urgent_care` 731; `subway_station` 496;
`post_office` 417; `atm` 342; `subway_line` 252; `hardware_store` 241;
`public_library` 214; `farmers_market` 127; `museum_institutional` 102;
`dog_run` 92; `hospital` 73; `path_station` 13; `ferry_terminal` 9;
`dry_cleaner` 7; `laundromat` 6. The originally planned individual-landmark
and public-art Socrata IDs (`s4sh-z6gg` and `zbs8-ab7x`) currently return 404s;
implementation uses the current LPC Individual Landmark Sites dataset
(`buis-pvji`) and the Public Design Commission Outdoor Public Art Inventory
(`2pg3-gcaa`). The historic district checklist item names the map view
`xbvj-gfnw`; implementation fetches its underlying current source dataset
`skyk-mpzq` so geometry and attributes are present.

### Wrap-Up

- [x] Implement `ingest_public_poi.py` fully (call `pipeline.run()`, print report)
- [x] Update `docs/pipeline_plan.md` — add `ingest_public_poi` step after `ingest_subway_stops`
- [x] Manual curation pass on urgent care rows (OSM `amenity=clinic` is noisy)
- [x] Verify `dim_public_poi` row counts by category look reasonable before wiring into scoring

Wrap-up completion summary: `ingest_public_poi.py` is now a runnable CLI entry
point with JSON report output, and `docs/pipeline_plan.md` includes the public
baseline POI step immediately after subway ingestion. The urgent-care loader now
applies a conservative manual curation pass over OSM `amenity=clinic` rows,
keeping urgent/immediate/walk-in care chains/providers and excluding obvious
specialty clinics, labs, dialysis, surgery, imaging, and non-NYC ZIP/city rows.
The verified run on 2026-04-23 wrote 56,540 rows to
`property_explorer_gold.dim_public_poi`, all with coordinates, across 27
categories. Curated `urgent_care` count is 142 rows. Current category counts:
`bike_lane` 28,983; `bus_stop` 11,523; `citi_bike_station` 2,406; `landmark`
1,629; `public_school` 1,595; `bank` 1,465; `grocery_store` 1,315; `park`
1,276; `pharmacy` 1,258; `playground` 1,011; `public_art` 775; `gym` 771;
`subway_station` 496; `post_office` 417; `atm` 342; `subway_line` 252;
`hardware_store` 241; `public_library` 214; `urgent_care` 142;
`farmers_market` 127; `museum_institutional` 102; `dog_run` 92; `hospital` 73;
`path_station` 13; `ferry_terminal` 9; `dry_cleaner` 7; `laundromat` 6.

Wave 3 implementation summary: Everyday retail baseline ingestion is now wired
into the public POI pipeline, with supermarket-style grocery rows from NYS DAM
retail food stores, laundromat/dry-cleaner rows from DCWP issued licenses, and
pharmacy/bank/ATM/hardware rows from OSM snapshots. The verified run on
2026-04-23 produced 50,695 total public POIs with complete coordinates; Wave 3
added 4,634 rows across seven categories.

---

## 1. New Database Table — `dim_public_poi`

Add `sql/ddl/002_public_poi_table.sql`:

```sql
CREATE SCHEMA IF NOT EXISTS property_explorer_gold;

CREATE TABLE IF NOT EXISTS property_explorer_gold.dim_public_poi (
    poi_id          VARCHAR,   -- sha256 hash: source_system|source_id
    source_system   VARCHAR,   -- "mta_gtfs" | "nyc_open_data" | "osm" | "gbfs" | "nypl_api" etc.
    source_id       VARCHAR,   -- native ID from the source dataset
    category        VARCHAR,   -- canonical category slug (see §3)
    subcategory     VARCHAR,   -- optional finer grain ("subway_entrance", "general_hospital", etc.)
    name            VARCHAR,
    address         VARCHAR,
    lat             DOUBLE,
    lon             DOUBLE,
    attributes      VARCHAR,   -- JSON: source-specific extras (lines served, acreage, season, etc.)
    snapshotted_at  TIMESTAMP  -- when the raw file was downloaded / snapshot taken
);
```

This table is written with `if_exists="replace"` on each full pipeline run, just like `dim_user_poi_v2`. The two tables stay independent — joining them in the app (or a view) is the right place to merge curated + baseline POIs.

---

## 2. Module Structure

Mirror the `google_places_poi/` layout exactly:

```
src/nyc_property_finder/public_poi/
├── __init__.py
├── config.py          # snapshot paths, category slugs, constants
├── build_dim.py       # normalize all sources → single DataFrame → dim_public_poi
├── pipeline.py        # orchestration: fetch/load snapshots → build → write DB
└── sources/
    ├── __init__.py
    ├── mta_subway.py      # GTFS subway stations + entrances + line geometry
    ├── mta_bus.py         # borough GTFS bus stops
    ├── gbfs_citibike.py   # Citi Bike GBFS station_information.json
    ├── osm.py             # pharmacies, banks, ATMs, hardware, post offices, gyms
    ├── nyc_open_data.py   # parks, dog runs, playgrounds, grocery, laundromats,
    │                      # dry cleaners, libraries (BPL/Queens), schools,
    │                      # farmers markets, hospitals, landmarks, DCLA museums
    ├── nypl_api.py        # NYPL Locations API (Manhattan + Staten Island branches)
    └── ferry_path.py      # NYC Ferry + PATH (small-N; OSM or hand-entry)
```

Pipeline entry point (matches existing pattern):

```
src/nyc_property_finder/pipelines/ingest_public_poi.py
```

Snapshot storage (raw downloads, never edited):

```
data/raw/public_poi/
    mta_subway/          gtfs_subway.zip already present at data/raw/transit/ — symlink or copy on first run
    mta_bus/             brooklyn.zip, bronx.zip, manhattan.zip, queens.zip, staten_island.zip
    citi_bike/           station_information_<date>.json
    nyc_open_data/       parks_properties_<date>.geojson, dog_runs_<date>.csv, ...
    osm/                 nyc_pharmacies_<date>.geojson, nyc_banks_<date>.geojson, ...
    nypl/                nypl_locations_<date>.json
```

---

## 3. Canonical Category Slugs

These are the `category` values written to `dim_public_poi`. Keep them stable — the app and scoring layer will filter on them.

| slug | source module |
|---|---|
| `subway_station` | mta_subway |
| `subway_entrance` | mta_subway |
| `subway_line` | mta_subway (geometry; lat/lon = centroid) |
| `bus_stop` | mta_bus |
| `citi_bike_station` | gbfs_citibike |
| `ferry_terminal` | ferry_path |
| `path_station` | ferry_path |
| `bike_lane` | nyc_open_data (geometry; lat/lon = centroid) |
| `park` | nyc_open_data |
| `dog_run` | nyc_open_data |
| `playground` | nyc_open_data |
| `public_library` | nyc_open_data + nypl_api |
| `post_office` | osm |
| `public_school` | nyc_open_data |
| `farmers_market` | nyc_open_data |
| `hospital` | nyc_open_data |
| `urgent_care` | osm |
| `pharmacy` | osm |
| `grocery_store` | nyc_open_data |
| `laundromat` | nyc_open_data |
| `dry_cleaner` | nyc_open_data |
| `gym` | osm |
| `bank` | osm |
| `atm` | osm |
| `hardware_store` | osm |
| `landmark` | nyc_open_data |
| `museum_institutional` | nyc_open_data |
| `public_art` | nyc_open_data |

---

## 4. Snapshot Strategy

Each source module has two responsibilities:

1. **`fetch_snapshot(output_dir)`** — downloads the raw file to `data/raw/public_poi/<source>/` with a datestamped filename. Idempotent: skips if today's file already exists. This is the only place network/HTTP calls happen.
2. **`load(snapshot_path) -> pd.DataFrame`** — reads the snapshot and returns a normalized DataFrame with columns `[source_system, source_id, category, subcategory, name, address, lat, lon, attributes]`. No network calls.

`pipeline.py` calls `fetch_snapshot()` for every source, then `load()` for each, then passes all frames to `build_dim.py` which concatenates, generates `poi_id` hashes, stamps `snapshotted_at`, and writes `dim_public_poi`.

Running the pipeline a second time on the same day reuses the existing snapshot files (no re-download).

---

## 5. Implementation Waves

Work in this order — each wave is independently runnable and testable before moving on.

---

### Wave 1 — Transit (highest signal, data mostly local)

**Subway stations & entrances** (`sources/mta_subway.py`)
- Input: `data/raw/transit/gtfs_subway.zip` (already present)
- Parse `stops.txt`: `stop_id`, `stop_name`, `stop_lat`, `stop_lon`, `location_type` (0=stop, 1=station, 2=entrance)
- Emit two categories: `subway_station` (location_type=1) and `subway_entrance` (location_type=2)
- `attributes`: `{"lines": ["A","C","E"]}` — derive from `stop_name` pattern or `routes.txt` join
- Note: `dim_subway_stop` already exists and is populated separately. `dim_public_poi` is the new home; the old table stays for backwards compat until the app migrates.

**Subway line geometry** (`sources/mta_subway.py`, same file)
- Parse `shapes.txt`, group by `shape_id` → derive centroid lat/lon for the `subway_line` category row
- `attributes`: `{"shape_id": "...", "point_count": N}`

**Bus stops** (`sources/mta_bus.py`)
- Source: MTA bus GTFS feeds, one zip per borough
- URLs (stable): `http://web.mta.info/developers/data/nyct/bus/google_transit_bronx.zip` (same pattern for other boroughs)
- `fetch_snapshot()` downloads all five; `load()` unions `stops.txt` from each, tags `subcategory` = borough name
- Deduplicate on `stop_id` (stops appear in multiple feeds if on a borough boundary)

**Citi Bike stations** (`sources/gbfs_citibike.py`)
- URL: `https://gbfs.citibikenyc.com/gbfs/en/station_information.json` (no key)
- `attributes`: `{"capacity": N, "region_id": "..."}` from GBFS payload
- category: `citi_bike_station`

**NYC Ferry + PATH** (`sources/ferry_path.py`)
- Small-N: hand-maintained CSV at `data/raw/public_poi/ferry_path/terminals.csv`
- Columns: `source_id, category, name, address, lat, lon, notes`
- `load()` reads this CSV directly; no `fetch_snapshot()` needed
- Add the 9 Ferry terminals and ~12 PATH stops as initial rows

**Bike-lane network** (`sources/nyc_open_data.py`)
- Dataset: NYC DOT "Bicycle Routes" — Socrata ID `s6d2-j7cd`
- Line features; emit one `bike_lane` row per feature with centroid lat/lon
- `attributes`: `{"route_name": "...", "facility_type": "Protected Path|Bike Lane|..."}` 

---

### Wave 2 — Parks & Recreation

All three datasets live in NYC Parks Open Data. Use the Socrata export URL pattern (GeoJSON or CSV):

**Parks** (`sources/nyc_open_data.py`)
- Dataset: "Parks Properties" — Socrata ID `enfh-gkve`
- Polygon features; derive centroid as lat/lon
- `attributes`: `{"gispropnum": "...", "acres": N, "typecategory": "..."}`
- Filter to `typecategory` in (`"Garden"`, `"Neighborhood Park"`, `"Flagship Park"`, `"Triangle/Plaza"`, `"Jointly Operated Playground"`) — exclude cemeteries, rights-of-way

**Dog runs** (`sources/nyc_open_data.py`)
- Dataset: "Dog Runs" — Socrata ID `hxx3-bwgv`
- Point features
- `attributes`: `{"on_leash": true/false, "fenced": true/false}` where available

**Playgrounds** (`sources/nyc_open_data.py`)
- Dataset: "Children's Play Areas" — Socrata ID `j55h-3upk`
- Point features

---

### Wave 3 — Everyday Retail Baseline

**Grocery stores / supermarkets** (`sources/nyc_open_data.py`)
- Dataset: NYC DOHMH "Retail Food Stores" — Socrata ID `9w7m-hzhe`
- Filter: `esttype` == `"FOOD SUPERMARKET"` or `"GROCERY STORE"`
- `attributes`: `{"esttype": "...", "license_number": "..."}`

**Pharmacies** (`sources/osm.py`)
- Overpass query: `[out:json]; area["name"="New York City"]->.nyc; node[amenity=pharmacy](area.nyc); out body;`
- Use the Overpass API endpoint: `https://overpass-api.de/api/interpreter`
- `fetch_snapshot()` writes the JSON response; `load()` parses nodes
- `attributes`: `{"brand": "...", "opening_hours": "..."}`

**Laundromats** (`sources/nyc_open_data.py`)
- Dataset: NYC DCWP "Legally Operating Businesses" — Socrata ID `w7w3-xahh`
- Filter: `industry` contains `"Laundry"` (industry code 110)

**Dry cleaners** (`sources/nyc_open_data.py`)
- Same DCWP dataset; filter industry code 113 ("Dry Cleaning")

**Banks / ATMs** (`sources/osm.py`)
- Two Overpass queries: `amenity=bank` and `amenity=atm`
- Emit as separate categories (`bank` vs `atm`)

**Hardware stores** (`sources/osm.py`)
- Overpass query: `shop=hardware`

---

### Wave 4 — Civic & Community

**Public libraries** — three systems merged into one category
- NYPL: `sources/nypl_api.py` — `https://refinery.nypl.org/api/nypl/locations/v1.0/locations` (no key required)
  - Filter: `locationTypes` includes `"Branch Library"`
- BPL (Brooklyn): `sources/nyc_open_data.py` — dataset `ukuu-ndnd` or hand-maintained CSV
- Queens Public Library: hand-maintained CSV (directory available at `queenslibrary.org`)
- All three merge into `category="public_library"`, `subcategory` = `"nypl" | "bpl" | "qpl"`

**Post offices** (`sources/osm.py`)
- Overpass: `amenity=post_office`

**Public schools** (`sources/nyc_open_data.py`)
- Dataset: NYC DOE "School Locations" — Socrata ID `r2nx-nhxe`
- `attributes`: `{"grade_high": "...", "grade_low": "...", "school_type": "..."}` — no quality ratings

**Farmers markets** (`sources/nyc_open_data.py`)
- Dataset: NYC DOHMH "Farmers Markets" — Socrata ID `8vwk-6iz2`
- `attributes`: `{"days_open": "...", "season_begin": "...", "season_end": "..."}`

**Hospitals** (`sources/nyc_open_data.py`)
- Dataset: NYC DOHMH "Health Facility General Information" or NYC Open Data "Hospitals" — Socrata ID `833h-xwsx`
- Filter to `facility_type == "General Hospital"` and `status == "OPEN"`

**Urgent care** (`sources/osm.py`)
- Overpass: `amenity=clinic` within NYC bounds
- Light manual curation pass after ingestion (OSM clinic tagging is noisy)
- `attributes`: `{"healthcare": "...", "opening_hours": "..."}`

**Gyms / fitness** (`sources/osm.py`)
- Overpass: `leisure=fitness_centre`
- Baseline only — curated studio list (Wave 5 of the expansion plan) will be in `dim_user_poi_v2`

---

### Wave 5 — Culture & Heritage

**Landmarks** (`sources/nyc_open_data.py`)
- Dataset: NYC LPC "Individual Landmarks" — Socrata ID `s4sh-z6gg`
- Also "Historic Districts" (polygon) — Socrata ID `xbvj-gfnw`; emit centroid as lat/lon
- `attributes`: `{"lm_type": "Individual Landmark|Interior Landmark|...", "borough": "..."}`

**Museums (institutional baseline)** (`sources/nyc_open_data.py`)
- Dataset: NYC DCLA "Cultural Institutions Group" — available via NYC Open Data
- `attributes`: `{"discipline": "...", "borough": "..."}`
- Deduplicate against `dim_user_poi_v2` at the app/view layer (not during ingestion)

**Public art / murals** (`sources/nyc_open_data.py`)
- Dataset: NYC Parks "Art in the Parks" — Socrata ID `zbs8-ab7x`
- Optional/low priority; add `subcategory="art_in_parks"`

---

## 6. `build_dim.py` Contract

Each source `load()` function returns a DataFrame with exactly these columns:

```python
NORMALIZED_COLUMNS = [
    "source_system",   # str: "mta_gtfs" | "nyc_open_data" | "osm" | "gbfs" | "nypl_api" | "hand_entry"
    "source_id",       # str: stable native ID from the source
    "category",        # str: slug from §3
    "subcategory",     # str | None
    "name",            # str
    "address",         # str | None
    "lat",             # float
    "lon",             # float
    "attributes",      # str: JSON
]
```

`build_dim.py` concatenates all frames, drops rows where `lat` or `lon` is null, generates `poi_id = sha256(f"{source_system}|{source_id}")[:16]`, stamps `snapshotted_at = datetime.utcnow()`, and returns the final DataFrame matching the `dim_public_poi` DDL.

---

## 7. Pipeline Entry Point

`src/nyc_property_finder/pipelines/ingest_public_poi.py`:

```python
from nyc_property_finder.public_poi.pipeline import run

report = run(
    database_path="data/processed/nyc_property_finder.duckdb",
    snapshot_dir="data/raw/public_poi",
    sources=None,   # None = all sources; list of slugs for partial runs
)
```

Invoke from the command line:

```bash
PYTHONPATH=src python -m nyc_property_finder.pipelines.ingest_public_poi
```

Add this step to the build sequence in `docs/pipeline_plan.md` after `ingest_subway_stops` and before `build_property_context`.

---

## 8. Execution Sequence

Build the waves in order. Each wave is independently committable.

| Step | Action | Files touched |
|---|---|---|
| 0 | Write DDL, run `init_database` to create `dim_public_poi` | `sql/ddl/002_public_poi_table.sql` |
| 1 | Scaffold `src/nyc_property_finder/public_poi/` with `config.py`, `build_dim.py`, `pipeline.py`, empty `sources/` | module structure |
| 2 | Wave 1: implement `mta_subway.py`, `mta_bus.py`, `gbfs_citibike.py`, `ferry_path.py`; add hand-entry CSV | `sources/` |
| 3 | Wave 2: implement parks/dog runs/playgrounds in `nyc_open_data.py` | `sources/nyc_open_data.py` |
| 4 | Wave 3: implement grocery/laundromat/dry cleaner in `nyc_open_data.py`; implement pharmacies/banks/hardware in `osm.py` | `sources/` |
| 5 | Wave 4: libraries, schools, hospitals, markets, urgent care, gyms | `sources/nypl_api.py`, `sources/nyc_open_data.py`, `sources/osm.py` |
| 6 | Wave 5: landmarks, institutional museums, public art | `sources/nyc_open_data.py` |
| 7 | Wire `pipeline.py` to call all sources; implement `ingest_public_poi.py` entry point | `pipeline.py`, `pipelines/` |
| 8 | Update `docs/pipeline_plan.md` with new build step | `docs/` |

Start with Step 0–2 to get end-to-end flow working on transit data before expanding to the full source list.

---

## 9. Open Questions (deferred)

- Google Places Nearby Search fallbacks for gyms and urgent care — defer until a specific user question demands it.
- Merging `dim_public_poi` + `dim_user_poi_v2` into a unified view for scoring — design that in `build_property_context` once both tables are populated.
- OSM snapshot cadence — monthly re-download is a reasonable default once the pipeline is stable.
