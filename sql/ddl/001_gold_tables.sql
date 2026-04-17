CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_tract_to_nta (
    tract_id VARCHAR,
    nta_id VARCHAR,
    nta_name VARCHAR,
    geometry_wkt VARCHAR
);

CREATE TABLE IF NOT EXISTS gold.dim_subway_stop (
    subway_stop_id VARCHAR,
    stop_name VARCHAR,
    lines VARCHAR,
    lat DOUBLE,
    lon DOUBLE
);

CREATE TABLE IF NOT EXISTS gold.dim_user_poi (
    poi_id VARCHAR,
    name VARCHAR,
    category VARCHAR,
    source_list_name VARCHAR,
    lat DOUBLE,
    lon DOUBLE
);

CREATE TABLE IF NOT EXISTS gold.dim_property_listing (
    property_id VARCHAR,
    source VARCHAR,
    source_listing_id VARCHAR,
    address VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    price DOUBLE,
    beds DOUBLE,
    baths DOUBLE,
    listing_type VARCHAR,
    url VARCHAR,
    ingest_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold.fct_tract_features (
    tract_id VARCHAR,
    median_income DOUBLE,
    median_rent DOUBLE,
    median_home_value DOUBLE,
    pct_bachelors_plus DOUBLE,
    median_age DOUBLE,
    crime_rate_proxy DOUBLE
);

CREATE TABLE IF NOT EXISTS gold.fct_nta_features (
    nta_id VARCHAR,
    nta_name VARCHAR,
    median_income DOUBLE,
    median_rent DOUBLE,
    median_home_value DOUBLE,
    pct_bachelors_plus DOUBLE,
    median_age DOUBLE,
    crime_rate_proxy DOUBLE
);

CREATE TABLE IF NOT EXISTS gold.fct_property_context (
    property_id VARCHAR,
    source VARCHAR,
    source_listing_id VARCHAR,
    address VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    price DOUBLE,
    beds DOUBLE,
    baths DOUBLE,
    listing_type VARCHAR,
    url VARCHAR,
    ingest_timestamp TIMESTAMP,
    tract_id VARCHAR,
    nta_id VARCHAR,
    nearest_subway_stop VARCHAR,
    nearest_subway_distance_miles DOUBLE,
    subway_lines_count INTEGER,
    poi_count_10min INTEGER,
    poi_category_counts VARCHAR,
    neighborhood_score DOUBLE,
    mobility_score DOUBLE,
    personal_fit_score DOUBLE,
    property_fit_score DOUBLE
);
