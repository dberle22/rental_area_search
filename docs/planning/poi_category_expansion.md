# POI Category Expansion Plan

Planning date: 2026-04-22

## Purpose

The Neighborhood Explorer currently has three POI categories loaded into
`dim_user_poi_v2` (Bookstores, Record Stores, Museums) plus seven more raw
Google Maps CSVs awaiting ingestion. This doc proposes the full target
category set, split into:

1. **Baseline public data** — high-coverage categories that should be sourced
   from public/open datasets and flow through a new `ingest_public_poi`
   pipeline (separate from Google Places billing).
2. **Curated taste-driven lists** — categories where editorial curation is the
   whole point, continuing through the existing Google Maps saved-list →
   Google Places v2 pipeline. For these, the "source" column points to the
   best-of-NYC sites worth mirroring into Maps.

Keeping the two tiers separate lets the app filter and score them differently
— "5+ grocery stores within 10 minutes" is a coverage question, while "near a
great natural wine bar" is a curation question.

## Table 1 — Baseline Public Data Categories

| Category | Primary Source | Notes |
| --- | --- | --- |
| Subway stations & entrances | MTA GTFS (`data/raw/transit/gtfs_subway.zip`, already local) + NYC Open Data "Subway Entrances" | Stations from `stops.txt`; entrances as separate points. |
| Subway line geometry | MTA GTFS `shapes.txt` or NYC Open Data "Subway Lines" | Line features for "near which lines" overlays. |
| Bus stops | MTA bus GTFS feeds (one per borough) | `stops.txt` in each feed. |
| Citi Bike stations | Citi Bike GBFS `station_information.json` | Public JSON, no key, updated live. |
| NYC Ferry terminals | NYC Ferry schedule site or OSM `amenity=ferry_terminal` | Small count, hand-entry viable. |
| PATH stations | PANYNJ data or OSM | Only relevant at Manhattan edges. |
| Bike-lane network | NYC DOT "Bicycle Routes" on NYC Open Data | Line features; feeds a bike-friendliness overlay. |
| Parks | NYC Parks "Parks Properties" on NYC Open Data | Polygons — derive centroid + acreage for ranking. |
| Dog runs | NYC Parks "Dog Runs" on NYC Open Data | Small but high signal for renters. |
| Playgrounds | NYC Parks "Playgrounds" on NYC Open Data | Relevant once a family profile exists. |
| Public libraries | NYPL Locations API + BPL open CSV + Queens Public Library directory | Three systems, merge into one category. |
| Post offices | USPS locator or OSM `amenity=post_office` | OSM sufficient. |
| Public schools | NYC DOE "School Locations" on NYC Open Data | Locations only; defer quality ratings. |
| Farmers markets | GrowNYC markets directory + NYC DOHMH "Farmers Markets" | GrowNYC has richer season/day metadata. |
| Hospitals | NYS DOH "Health Facility General Information" + NYC Open Data | Filter to active general hospitals. |
| Urgent care | OSM `amenity=clinic` + manual curation | No clean public feed; Google Places Nearby Search is fallback. |
| Pharmacies | OSM `amenity=pharmacy` | Excellent chain coverage in NYC (CVS, Duane Reade, Walgreens, Rite Aid). |
| Grocery stores / supermarkets | NYS DOH / NYC DOHMH "Retail Food Stores" | Filterable to supermarkets vs. bodegas. |
| Laundromats | NYC DCWP "Legally Operating Businesses" on NYC Open Data | Filter by industry code. |
| Dry cleaners | NYC DCWP "Legally Operating Businesses" | Same dataset, different code. |
| Gyms / fitness (baseline) | OSM `leisure=fitness_centre` | Supplement with Google Places Nearby Search if coverage is thin. |
| Banks / ATMs | OSM `amenity=bank` / `amenity=atm` | Good NYC coverage. |
| Hardware stores | OSM `shop=hardware` | Good coverage for True Value, Ace, etc. |
| Landmarks (official) | NYC Landmarks Preservation Commission "Individual Landmarks" + "Historic Districts" | Provides both points and district polygons. |
| Museums (institutional baseline) | NYC DCLA "Cultural Institutions Group" + DCLA grantees | Complements the curated `Museums.csv`. |
| Public art / murals | NYC Parks "Art in the Parks" + NYC DOT "Asphalt Art" | Optional; raises cultural density signal. |

## Table 2 — Curated Taste-Driven Categories

For every row here, the workflow is the same: use the listed sources to build
a Google Maps saved list, export via Takeout into `data/raw/google_maps/`,
then run `pipelines.ingest_google_places_poi`.

| Category | Best-of-NYC Sources | Notes |
| --- | --- | --- |
| Bookstores | Literary Hub "Best Independent Bookstores in NYC"; Independent Bookstore Day NYC participant list; Bookstore.fm curated lists | Already in `dim_user_poi_v2` (37 rows) — use these for refresh. |
| Record Stores | Discogs "Best Record Stores in NYC"; Pitchfork NYC guide; Record Store Day NYC participant list | Already in `dim_user_poi_v2` (29 rows). |
| Museums (curated) | Existing `Museums.csv` + `New York - Museums.csv` | In `dim_user_poi_v2` (25 rows). Dedupe vs. Tier 1 DCLA baseline. |
| Restaurants (general) | Eater NYC "38 Essential Restaurants"; The Infatuation "Hit List"; NYT "100 Best Restaurants in NYC"; Michelin Guide NYC (esp. Bib Gourmand); Resy "Hit List" | Raw CSV exists, not yet ingested. Consider splitting into Date-night / Neighborhood / Destination once volume grows. |
| Pizza | Eater NYC "Essential Pizza Map"; Scott's Pizza Tours stop lists; Pete Wells NYT pizza reviews | Raw CSV exists, not yet ingested. |
| Bars (cocktail) | Eater NYC "Essential Bars"; Punch; Liquor.com; World's 50 Best Bars (NYC entries) | Raw CSVs exist (`Bars.csv`, `Bars - NYC.csv`). Recommend sub-splitting into Cocktail / Wine / Dive. |
| Bars (wine / natural wine) | PUNCH "Best Wine Bars in NYC"; Eater wine bar guides | New sub-list. |
| Bars (dive / neighborhood) | Time Out "Best Dive Bars"; The Infatuation neighborhood bar guides | New sub-list. |
| Coffee shops | Sprudge NYC guides; Eater "Essential Coffee Shops"; The Infatuation coffee guides | New category — highest-leverage taste addition. |
| Bakeries / pastry shops | Eater "Best Bakeries in NYC"; The Infatuation "Best Pastries"; Bon Appétit "Best New Bakeries" (filter to NYC) | Raw CSV exists (`Pastry Shops.csv`), not yet ingested. |
| Food markets / food halls | Hand-built from: Essex Market, Chelsea Market, Smorgasburg, DeKalb Market Hall, Time Out Market, Industry City, Urbanspace locations | Small-N list, no editorial source needed. |
| Specialty grocery | Serious Eats "Best Specialty Grocers"; Eater "Best Specialty Food Shops" | Complements Tier 1 supermarket baseline. |
| Specialty cuisine (ramen, dumplings, bagels, tacos, dim sum, Thai, Indian, delis, etc.) | Eater NYC per-cuisine "essential" maps | One list per cuisine. Add as dedicated categories once base Restaurants list is stable. |
| Shopping (general) | The Strategist (New York Magazine) category lists; Racked NYC archives; Time Out NYC shopping guides | Raw CSV exists (`Shopping.csv`), not yet ingested. |
| Vintage / thrift | The Strategist "Best Vintage Stores in NYC"; L Train Vintage / Beyond Retro directories | Sub-list candidate if volume grows. |
| Live music venues | Brooklyn Vegan venue guides; Pitchfork NYC guides; Time Out "Best Live Music Venues" | Consider sub-splitting by size: small / mid / large. |
| Movie theaters (repertory / arthouse) | Screen Slate daily listings (defines the canonical set); Letterboxd NYC repertory lists | Metrograph, Film Forum, IFC Center, Nitehawk, Alamo, BAM, Film at Lincoln Center, Quad, Roxy, Paris. |
| Theaters (non-film) | TDF / Playbill venue directories; American Theatre Wing member theaters | Broadway + off-Broadway + neighborhood. |
| Art galleries | Artforum "Critics' Picks" NYC archive; Gallery Platform NYC; Contemporary Art Daily NYC coverage | Sub-list by district (Chelsea / LES / Tribeca / Bushwick). |
| Comedy clubs | Vulture "Best Comedy Clubs in NYC"; Time Out comedy guides | Small list: Comedy Cellar, UCB, The Stand, NYCC, Union Hall, etc. |
| Jazz / intimate music rooms | Time Out "Best Jazz Clubs"; All About Jazz NYC venue guide | Distinct from general live music. |
| Yoga / fitness studios (curated) | Well+Good NYC studio guides; Class Pass popular studios | Tier 2 overlay on top of the Tier 1 gym baseline. |
| Running clubs / run-friendly spots | NY Road Runners affiliated clubs; Time Out "Best Running Routes" | Mostly parks + track points. |
| Swimming pools (private) | The Strategist / Time Out pool guides | Public pools come from Tier 1 NYC Parks data. |

## Sequencing

A rough order that front-loads high-signal additions while keeping ingestion
tractable:

1. **Finish the existing raw CSVs** (Bars, Pastry Shops, Pizza, Restaurants,
   Shopping). Review's Priority 1 — zero new sourcing work.
2. **Tier 1 transit and parks.** Subway entrances, bus stops, Citi Bike,
   parks, dog runs, playgrounds.
3. **Tier 1 everyday retail baseline.** Grocery (DOHMH), pharmacies (OSM),
   laundromats (DCWP), banks (OSM).
4. **Tier 1 libraries, schools, hospitals, farmers markets.**
5. **Tier 2 coffee shops (new)** + refresh of existing curated lists.
6. **Tier 2 sub-list splits.** Bars → Cocktail / Wine / Dive. Shopping →
   Fashion / Vintage / Home. Split Restaurants only if it grows past ~200.
7. **Tier 2 culture expansion.** Live music, repertory cinemas, galleries,
   comedy.
8. **Specialty food categories.** Ramen, dumplings, bagels, tacos, etc.

## Not Yet

Per the review's caution about premature precision:

- **Crime/safety.** Defer until source and framing are strong.
- **School quality ratings.** School locations are fine (Tier 1); ratings
  need clearer framing first.
- **"Best neighborhoods" overlays.** Belong in derived summary views, not as
  a POI category.

## Open Questions

- `dim_public_poi` as its own table or a `source_type` column on
  `dim_user_poi_v2`? Separate table is cleaner given different billing and
  update cadences, but adds a join in the app.
- For OSM-sourced categories, re-query per build or snapshot a dated extract?
  Re-query is simpler; snapshot is more reproducible.
- For Google Places Nearby Search fallbacks (gyms, urgent care), is the
  billing worth it vs. accepting OSM gaps? Probably defer until a specific
  user question demands it.
