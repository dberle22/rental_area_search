CREATE SCHEMA IF NOT EXISTS property_explorer_gold;

CREATE TABLE IF NOT EXISTS property_explorer_gold.dim_tract_to_nta (
    tract_id VARCHAR,
    nta_id VARCHAR,
    nta_name VARCHAR,
    borough VARCHAR,
    cdta_id VARCHAR,
    cdta_name VARCHAR,
    geometry_wkt VARCHAR
);

CREATE TABLE IF NOT EXISTS property_explorer_gold.dim_subway_stop (
    subway_stop_id VARCHAR,
    stop_name VARCHAR,
    lines VARCHAR,
    lat DOUBLE,
    lon DOUBLE
);

CREATE TABLE IF NOT EXISTS property_explorer_gold.dim_user_poi (
    poi_id VARCHAR,
    name VARCHAR,
    category VARCHAR,
    source_list_name VARCHAR,
    lat DOUBLE,
    lon DOUBLE
);

CREATE TABLE IF NOT EXISTS property_explorer_gold.dim_user_poi_v2 (
    poi_id VARCHAR,
    source_system VARCHAR,
    source_record_id VARCHAR,
    source_list_names VARCHAR,
    categories VARCHAR,
    primary_category VARCHAR,
    name VARCHAR,
    input_title VARCHAR,
    note VARCHAR,
    tags VARCHAR,
    comment VARCHAR,
    source_url VARCHAR,
    google_place_id VARCHAR,
    match_status VARCHAR,
    address VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    details_fetched_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS property_explorer_gold.dim_property_listing (
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
    active BOOLEAN,
    url VARCHAR,
    ingest_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS property_explorer_gold.fct_tract_features (
    tract_id VARCHAR,
    median_income DOUBLE,
    median_rent DOUBLE,
    median_home_value DOUBLE,
    pct_bachelors_plus DOUBLE,
    median_age DOUBLE,
    crime_rate_proxy DOUBLE
);

CREATE TABLE IF NOT EXISTS property_explorer_gold.fct_nta_features (
    nta_id VARCHAR,
    nta_name VARCHAR,
    median_income DOUBLE,
    median_rent DOUBLE,
    median_home_value DOUBLE,
    pct_bachelors_plus DOUBLE,
    median_age DOUBLE,
    crime_rate_proxy DOUBLE
);

CREATE TABLE IF NOT EXISTS property_explorer_gold.fct_property_context (
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
    active BOOLEAN,
    url VARCHAR,
    ingest_timestamp TIMESTAMP,
    tract_id VARCHAR,
    nta_id VARCHAR,
    nta_name VARCHAR,
    nearest_subway_stop VARCHAR,
    nearest_subway_distance_miles DOUBLE,
    subway_lines_count INTEGER,
    poi_data_available BOOLEAN,
    poi_count_nearby INTEGER,
    poi_count_10min INTEGER,
    poi_category_counts VARCHAR,
    neighborhood_score DOUBLE,
    neighborhood_score_status VARCHAR,
    mobility_score DOUBLE,
    personal_fit_score DOUBLE,
    personal_fit_score_status VARCHAR,
    property_fit_score DOUBLE,
    property_fit_score_status VARCHAR
);

CREATE TABLE IF NOT EXISTS property_explorer_gold.fct_user_shortlist (
    shortlist_id VARCHAR,
    user_id VARCHAR,
    property_id VARCHAR,
    saved_timestamp TIMESTAMP,
    updated_timestamp TIMESTAMP,
    status VARCHAR,
    notes VARCHAR,
    metadata_json VARCHAR
);
