# Architecture

NYC Property Finder follows a lightweight medallion pattern:

- Bronze: raw files and API exports
- Silver: cleaned source-specific tables
- Gold: analytics-ready dimensions and facts used by the app

DuckDB is the local analytical database. GeoPandas performs spatial operations
before writing tabular outputs back to DuckDB.
