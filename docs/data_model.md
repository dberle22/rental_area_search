# Data Model

Core gold tables:

- `dim_tract_to_nta`
- `dim_user_poi`
- `dim_property_listing`
- `fct_tract_features`
- `fct_property_context`

Geometry is stored as WKT in DuckDB for the starter version. Active spatial
logic uses GeoPandas objects in pipeline code.
