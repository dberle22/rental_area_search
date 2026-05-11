create schema if not exists neighborhood_character_mart;

create table if not exists neighborhood_character_mart.nta_boundaries (
    nta_id varchar,
    nta_name varchar,
    borough varchar,
    area_sqkm double,
    centroid_lat double,
    centroid_lon double,
    geometry_wkt varchar
);

create table if not exists neighborhood_character_mart.nta_poi_assignments (
    poi_id varchar,
    poi_source varchar,
    nta_id varchar,
    category varchar,
    subcategory varchar,
    lat double,
    lon double
);

create table if not exists neighborhood_character_mart.nta_curated_poi_counts (
    nta_id varchar,
    nta_name varchar,
    borough varchar,
    category varchar,
    subcategory varchar,
    poi_count integer,
    nyc_category_total integer
);

create table if not exists neighborhood_character_mart.nta_public_poi_counts (
    nta_id varchar,
    nta_name varchar,
    borough varchar,
    category varchar,
    poi_count integer
);

create table if not exists neighborhood_character_mart.nta_category_density (
    nta_id varchar,
    nta_name varchar,
    borough varchar,
    area_sqkm double,
    source varchar,
    category varchar,
    poi_count integer,
    poi_density_per_sqkm double,
    subcategory_diversity integer,
    nyc_category_total integer,
    nyc_percentile double,
    concentration_tier varchar,
    meets_evidence_threshold boolean
);

create table if not exists neighborhood_character_mart.nta_category_controls (
    category varchar,
    include_in_explore_v1 boolean,
    known_for_enabled boolean,
    min_nyc_category_total integer,
    display_label varchar,
    notes varchar
);

create table if not exists neighborhood_character_mart.nta_character_profile (
    nta_id varchar,
    nta_name varchar,
    borough varchar,
    area_sqkm double,
    total_curated_poi_count integer,
    destination_categories varchar,
    strong_categories varchar,
    top_category varchar,
    top_subcategory varchar,
    subway_station_count integer,
    bus_stop_count integer,
    grocery_store_count integer,
    pharmacy_count integer,
    park_count integer,
    public_library_count integer,
    public_school_count integer,
    built_at timestamp
);
