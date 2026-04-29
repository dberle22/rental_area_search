# POI Categories Reference

This is the taxonomy source of truth for NYC Area Mapper POIs.

We maintain two active POI families:

- **Curated**: personal or editorial taste-driven places resolved through Google Places and loaded into `dim_user_poi_v2`
- **Public**: baseline open-data or official-source places loaded into `dim_public_poi`

When needed, taxonomy can go deeper than one level:

- `category`: top-level group used for broad filtering and modeling
- `subcategory`: drill-down within a category
- `detail_level_3`: optional deeper label when a category needs more structure

---

## Taxonomy Rules

### Curated taxonomy

- Curated source of truth lives in `data/raw/google_maps/poi_nyc/`
- Curated restaurant-family files should roll up to `category=restaurants`
- `subcategory` should be the one stable, primary bucket used for filtering
- Use file identity first for `subcategory`, then fall back to `Tags` or `Comment` when the file is intentionally mixed
- Keep raw `tags` and `comment` values even when taxonomy is derived from them
- If a curated file represents a broad list, `subcategory` may be blank until a reliable rule exists
- `detail_level_3` should be treated as a flexible descriptor layer, not a strict hierarchy
- A row may effectively have multiple level-3 descriptors, for example a sandwich shop tagged as both `deli` and `italian`
- For restaurant cuisine families, a good rule of thumb is:
  `subcategory` = stable cuisine or format bucket such as `japanese`, `pizza`, or `sandwiches`
  `detail_level_3` = more specific descriptors such as `ramen`, `sushi`, `izakaya`, `deli`, or `italian`

### Public taxonomy

- Public POIs should use stable source-driven categories
- `subcategory` should capture source-native distinctions that are helpful in the UI or QA
- `detail_level_3` is optional and usually not needed unless a source exposes a meaningful third layer

---

## Curated Taxonomy (`dim_user_poi_v2`)

Build process: curate a Google Maps saved list or other curated source, export
or normalize to CSV, save under `data/raw/google_maps/poi_nyc/`, then run
`ingest_google_places_poi`.

| Category | Subcategory | Detail Level 3 | File / Source | Status | Notes / Source Sites |
| --- | --- | --- | --- | --- | --- |
| bookstores | independent_bookstores |  | `poi_bookstores_nyc.csv` | raw | Literary Hub; Independent Bookstore Day NYC; Bookstore.fm |
| record_stores | record_stores |  | `poi_record_stores_nyc.csv` | raw | Discogs NYC guide; Pitchfork NYC; Record Store Day NYC |
| museums | museums |  | `poi_museums_nyc.csv` | raw | Previous curated list + `New York - Museums.csv` |
| restaurants | tag-derived when available | flexible cuisine or format tags | `poi_restaurants_nyc.csv` | raw | Mixed restaurant list. Use `Tags`/`Comment` to derive the primary subcategory when reliable. Sources: Eater NYC "38 Essential"; The Infatuation Hit List; NYT 100 Best; Michelin Bib Gourmand; Resy Hit List |
| restaurants | pizza |  | `poi_pizza_nyc.csv` | raw | Eater NYC essential pizza map; Scott's Pizza Tours; Pete Wells NYT reviews |
| restaurants | chinese |  | `poi_rest_chinese_nyc.csv` | raw | Eater NYC Chinese essential map |
| restaurants | japanese | ramen, sushi, izakaya | `poi_rest_japanese_nyc.csv` | raw | Eater NYC Japanese essential map |
| restaurants | sandwiches | deli, italian, hero-style tags as needed | `poi_sandwich_nyc.csv` | raw | Eater NYC; The Infatuation sandwich guides |
| bars | tag-derived when available | flexible bar descriptors | `poi_bars_nyc.csv` | raw | Irish pub should live at subcategory level when tagged that way. Other bar style tags can remain level 3. Sources: Eater NYC essential bars; Punch; Liquor.com |
| bakeries | bakeries | pastry_shop if split later | `poi_bakeries_nyc.csv` | raw | Eater "Best Bakeries"; The Infatuation; Bon Appétit |
| coffee_shops | coffee_shops |  | `poi_cafe_nyc.csv` | raw | Sprudge NYC; Eater "Essential Coffee Shops"; The Infatuation |
| food_markets |  | rely mainly on tags until a stable subcategory set exists | `poi_markets_nyc.csv` | raw | Essex Market, Chelsea Market, Smorgasburg, DeKalb, Time Out Market, Industry City |
| specialty_grocery | specialty_grocery |  | `poi_speciality_food_market.csv` | raw | Serious Eats; Eater "Best Specialty Food Shops" |
| movie_theaters | movie_theaters | repertory_theater if split later | `poi_movie_theaters_nyc.csv` | raw | Screen Slate; Letterboxd NYC repertory lists |
| music_venues |  | rely mainly on tags until a stable subcategory set exists | `poi_music_venue_nyc.csv` | raw | Brooklyn Vegan; Pitchfork NYC; Time Out NYC |

### Curated legacy root-level files

These files in `data/raw/google_maps/` predate the `poi_nyc/` directory.
Superseded files should not be re-ingested once their `poi_nyc/` replacement is
loaded.

| File | Category | Subcategory | Notes |
| --- | --- | --- | --- |
| `New York - Bookstores.csv` | bookstores | independent_bookstores | Loaded previously; superseded by `poi_bookstores_nyc.csv` |
| `New York - Record Stores.csv` | record_stores | record_stores | Loaded previously; superseded by `poi_record_stores_nyc.csv` |
| `Museums.csv` + `New York - Museums.csv` | museums | museums | Loaded previously; superseded by `poi_museums_nyc.csv` |
| `Bars.csv` + `Bars - NYC.csv` | bars | bars | Not ingested; superseded by `poi_bars_nyc.csv` |
| `Pastry Shops.csv` | bakeries | bakeries | Not ingested; superseded by `poi_bakeries_nyc.csv` |
| `Pizza.csv` | restaurants | pizza | Not ingested; superseded by `poi_pizza_nyc.csv` |
| `Restaurants.csv` | restaurants | tag-derived when available | Not ingested; superseded by `poi_restaurants_nyc.csv` |
| `Shopping.csv` | shopping | shopping | Not ingested; no `poi_nyc/` replacement yet |

---

## Public Taxonomy (`dim_public_poi`)

All 5 public POI waves are complete as of 2026-04-23. Re-run
`ingest_public_poi` to refresh source snapshots.

| Category | Subcategory | Detail Level 3 | Source system | Dataset / Source | Row count |
| --- | --- | --- | --- | --- | --- |
| transit | subway_station | station | MTA GTFS | `data/raw/transit/gtfs_subway.zip` (`stops.txt`, location_type=1) | 496 |
| transit | subway_station | entrance | MTA GTFS | `data/raw/transit/gtfs_subway.zip` entrances | included in table; separate public slug today is `subway_entrance` |
| transit | subway_line | shape_centroid | MTA GTFS | `shapes.txt` centroids | 252 |
| transit | bus_stop | borough-specific stop type | MTA GTFS | Borough GTFS feeds (5 zips), unioned on `stop_id` | 11,523 |
| micromobility | citi_bike_station | station | GBFS | `gbfs.citibikenyc.com/gbfs/en/station_information.json` | 2,406 |
| transit | ferry_terminal |  | Hand entry | `data/raw/public_poi/ferry_path/terminals.csv` | 9 |
| transit | path_station |  | Hand entry | `data/raw/public_poi/ferry_path/terminals.csv` | 13 |
| mobility_infra | bike_lane |  | NYC Open Data | Socrata `mzxg-pwib` (Bicycle Routes) | 28,983 |
| parks_recreation | park | recreational park type | NYC Open Data | Socrata `enfh-gkve` (Parks Properties) | 1,276 |
| parks_recreation | playground | play area type | NYC Open Data | Socrata `j55h-3upk` (Children's Play Areas) | 1,011 |
| parks_recreation | dog_run |  | NYC Open Data | Socrata `hxx3-bwgv` (Dog Runs) | 92 |
| daily_needs | grocery_store | supermarket | NYS DAM | Socrata `9a8c-vfzj` (Retail Food Stores), supermarket filter | 1,315 |
| daily_needs | pharmacy | pharmacy | OSM | Overpass `amenity=pharmacy` | 1,258 |
| daily_needs | laundromat | dcwp_license_type | NYC Open Data | Socrata `w7w3-xahh` (DCWP businesses) | 6 |
| daily_needs | dry_cleaner | dcwp_license_type | NYC Open Data | Socrata `w7w3-xahh` (DCWP businesses) | 7 |
| daily_needs | bank | bank | OSM | Overpass `amenity=bank` | 1,465 |
| daily_needs | atm | atm | OSM | Overpass `amenity=atm` | 342 |
| daily_needs | hardware_store | hardware | OSM | Overpass `shop=hardware` | 241 |
| civic | public_library | nypl / bpl / qpl | NYPL API + NYC Open Data + CSV | NYPL Refinery API; Socrata `feuq-due4`; Socrata `kh3d-xhq7` | 214 |
| civic | post_office | post_office | OSM | Overpass `amenity=post_office` | 417 |
| civic | public_school | school_type | NYC Open Data | Socrata `r2nx-nhxe` (DOE School Locations) | 1,595 |
| food_access | farmers_market | market_type | NYC Open Data | Socrata `8vwk-6iz2` (DOHMH Farmers Markets) | 127 |
| health_care | hospital | facility_type | NYC Open Data | Socrata `ji82-xba5` (DCP Facilities Database) | 73 |
| health_care | urgent_care | urgent_care | OSM (curated) | Overpass `amenity=clinic`, filtered to urgent/walk-in care | 142 |
| fitness | gym | fitness_centre | OSM | Overpass `leisure=fitness_centre` | 771 |
| culture | landmark | landmark_type | NYC Open Data | Socrata `buis-pvji` (LPC Individual Landmarks); `skyk-mpzq` (Historic Districts) | 1,629 |
| culture | museum_institutional | museum | NYC Open Data | DCLA Cultural Institutions Group | 102 |
| culture | public_art | artwork_type | NYC Open Data | Socrata `2pg3-gcaa` (Public Design Commission Outdoor Art) | 775 |

---

## Planned Curated Scraped Inputs

These are future curated sources that should map into the same taxonomy as
`dim_user_poi_v2`.

| Category | Subcategory | Target Article / Source | Status |
| --- | --- | --- | --- |
| restaurants | mixed_restaurants | Eater NYC "38 Essential Restaurants" | planned |
| restaurants | mixed_restaurants | NYT "100 Best Restaurants in NYC" | planned |
| bars | bars | Eater NYC "Essential Bars" | planned |
| coffee_shops | coffee_shops | Sprudge NYC guide | planned |
| bakeries | bakeries | Bon Appétit "Best New Bakeries" (NYC filter) | planned |
| restaurants | pizza | Eater NYC essential pizza map | planned |
| music_venues | music_venues | Brooklyn Vegan NYC venue list | planned |
| art_galleries | art_galleries | Artforum "Critics' Picks" NYC archive | planned |

---

## How to Add a New Curated Entry

1. Create or collect the curated list.
2. Decide its `category`, `subcategory`, and optional `detail_level_3`.
3. Export or normalize to CSV and save it to `data/raw/google_maps/poi_nyc/`.
4. Add an entry to the curated taxonomy table above with status `raw`.
5. If file-level taxonomy is ambiguous, define the rule for deriving it from `Tags` or `Comment`.
6. Update `config/poi_categories.yaml` and any pipeline normalization rules as needed.
7. Run `ingest_google_places_poi`.
8. Update status to `loaded` with row counts after QA.

## How to Add a New Public Entry

1. Identify the source dataset.
2. Decide its `category`, `subcategory`, and optional `detail_level_3`.
3. Add or update the source loader under `src/nyc_property_finder/public_poi/sources/`.
4. Wire the category into the public POI pipeline.
5. Run `ingest_public_poi` and verify row counts.
6. Add or update the entry in the public taxonomy table above.
