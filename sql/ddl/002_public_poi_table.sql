CREATE SCHEMA IF NOT EXISTS property_explorer_gold;

CREATE TABLE IF NOT EXISTS property_explorer_gold.dim_public_poi (
    poi_id VARCHAR,
    source_system VARCHAR,
    source_id VARCHAR,
    category VARCHAR,
    subcategory VARCHAR,
    name VARCHAR,
    address VARCHAR,
    lat DOUBLE,
    lon DOUBLE,
    attributes VARCHAR,
    snapshotted_at TIMESTAMP
);
