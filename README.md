# NYC Property Finder

NYC Property Finder is a starter Python data product for evaluating rental or
purchase listings with neighborhood, mobility, and personal POI context.

The project uses:

- `src/` package layout
- DuckDB for local analytical storage
- GeoPandas/Shapely for spatial joins and distance calculations
- Streamlit and PyDeck for the map explorer
- Pytest for starter behavior tests

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Run Tests

```bash
.venv/bin/pytest
```

## Initialize Database

```bash
.venv/bin/python -m nyc_property_finder.pipelines.init_database
```

This creates the DuckDB database configured in `config/settings.yaml` and runs
the SQL files in `sql/ddl/`.

## Starter Local Ingestion

The MVP build path is file-backed first, so development does not depend on live
listing scraping.

```bash
.venv/bin/python -m nyc_property_finder.pipelines.init_database
```

Pipeline modules currently expose Python `run(...)` functions for:

- `nyc_property_finder.pipelines.ingest_property_file`: load local CSV/JSON property listings.
- `nyc_property_finder.pipelines.ingest_subway_stops`: load local CSV/JSON subway stops.
- `nyc_property_finder.pipelines.ingest_google_maps`: load Google Maps KML/JSON saved places.
- `nyc_property_finder.pipelines.build_property_context`: build and persist scored property context.

## Run App

```bash
streamlit run app/streamlit_app.py
```

## Project Layout

```text
config/                         YAML settings and source metadata
data/raw/                       Raw source files
data/interim/                   Temporary pipeline outputs
data/processed/                 DuckDB database and processed artifacts
src/nyc_property_finder/        Python package
app/                            Streamlit app
tests/                          Unit tests
```

## Starter Pipelines

- `build_tract_to_nta.py`: load tract/NTA geometries and assign tracts by centroid.
- `ingest_google_maps.py`: parse KML/JSON saved places and normalize POI categories.
- `ingest_property_file.py`: normalize local CSV/JSON listing exports.
- `ingest_subway_stops.py`: normalize local CSV/JSON subway stop files.
- `build_neighborhood_features.py`: ACS/crime placeholder feature builder.
- `ingest_property_streeteasy.py`: scraper-shaped StreetEasy ingestion skeleton.
- `build_property_context.py`: join property geography, transit, POIs, and starter scores.

The implementation is intentionally simple and modular. TODO comments mark the
places where real source-specific logic should replace placeholders.
