-- property_classification_mart DDL
-- Purpose: isolate Stoop place/property classification workflow tables.
-- Database target: DuckDB

create schema if not exists property_classification_mart;

-- ============================================================
-- 1. Classification text
-- One row per source place with combined text used for classification.
-- Source table is expected to exist outside this schema.
-- ============================================================

create table if not exists property_classification_mart.place_classification_text (
    poi_id varchar not null,
    name varchar,

    current_category varchar,
    current_subcategory varchar,
    current_detail_level_3 varchar,

    source_system varchar,
    source_list_names_raw varchar,
    tags_raw varchar,
    comment_raw varchar,
    editorial_summary_raw varchar,

    classification_text_raw varchar,
    classification_text_clean varchar,
    source_list_names_clean varchar,
    tags_clean varchar,
    comment_clean varchar,
    editorial_summary_clean varchar,

    has_comment boolean,
    has_editorial_summary boolean,
    has_source_list_names boolean,
    has_tags boolean,

    created_at timestamp default current_timestamp,

    primary key (poi_id)
);

-- ============================================================
-- 2. Word profile
-- Exploratory table for single word frequency analysis.
-- Rebuildable output table.
-- ============================================================

create table if not exists property_classification_mart.place_word_profile (
    token varchar not null,
    analysis_domain varchar default 'restaurant',
    analysis_segment varchar default 'all_restaurants',

    token_count integer,
    place_count integer,
    place_share double,
    example_places varchar,

    created_at timestamp default current_timestamp,

    primary key (token, analysis_domain, analysis_segment)
);

-- ============================================================
-- 3. Phrase profile
-- Exploratory table for two and three word phrase frequency analysis.
-- Rebuildable output table.
-- ============================================================

create table if not exists property_classification_mart.place_phrase_profile (
    phrase varchar not null,
    phrase_length integer not null,
    analysis_domain varchar default 'restaurant',
    analysis_segment varchar default 'all_restaurants',

    phrase_count integer,
    place_count integer,
    place_share double,
    example_places varchar,

    created_at timestamp default current_timestamp,

    primary key (phrase, phrase_length, analysis_domain, analysis_segment)
);

-- ============================================================
-- 4. Keyword mapping
-- Controlled rules table. Manually maintained and improved over time.
-- This is the core classification mapping table.
-- ============================================================

create table if not exists property_classification_mart.place_keyword_mapping (
    keyword_id varchar not null,

    keyword varchar not null,
    keyword_clean varchar not null,
    match_type varchar default 'contains',

    place_domain varchar default 'restaurants',

    mapped_category varchar not null,
    mapped_subcategory varchar not null,
    mapped_detail_level_3 varchar,

    keyword_role varchar,
    weight integer default 1,
    priority integer default 100,

    active_flag boolean default true,
    notes varchar,

    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp,

    primary key (keyword_id)
);

create unique index if not exists idx_place_keyword_mapping_keyword_domain
    on property_classification_mart.place_keyword_mapping(
        keyword_clean,
        place_domain,
        mapped_category,
        mapped_subcategory,
        mapped_detail_level_3
    );

-- ============================================================
-- 5. Keyword matches
-- One row per place per matched keyword/source-field combination.
-- This is the explainability layer.
-- ============================================================

create table if not exists property_classification_mart.place_keyword_matches (
    poi_id varchar not null,
    place_name varchar,

    keyword_id varchar not null,
    keyword varchar not null,
    match_type varchar,
    place_domain varchar,
    source_field varchar not null,

    mapped_category varchar,
    mapped_subcategory varchar,
    mapped_detail_level_3 varchar,

    keyword_role varchar,
    base_weight integer,
    source_weight integer,
    effective_weight integer,
    priority integer,

    created_at timestamp default current_timestamp,

    primary key (poi_id, keyword_id, source_field)
);

create index if not exists idx_place_keyword_matches_place
    on property_classification_mart.place_keyword_matches(poi_id);

create index if not exists idx_place_keyword_matches_mapping
    on property_classification_mart.place_keyword_matches(
        mapped_category,
        mapped_subcategory,
        mapped_detail_level_3
    );

-- ============================================================
-- 6. Matched keywords by place
-- One row per place with aggregated matched keyword fields.
-- This supports review and downstream summaries.
-- ============================================================

create table if not exists property_classification_mart.place_matched_keywords (
    poi_id varchar not null,
    place_name varchar,

    matched_keywords varchar,
    matched_keyword_count integer,

    matched_type_keywords varchar,
    matched_cuisine_keywords varchar,
    matched_vibe_keywords varchar,
    matched_format_keywords varchar,
    matched_occasion_keywords varchar,
    matched_quality_signal_keywords varchar,

    total_keyword_weight integer,

    created_at timestamp default current_timestamp,

    primary key (poi_id)
);

-- ============================================================
-- 7. Classification scores
-- One row per place per candidate classification.
-- Scores are aggregated from matched keyword weights.
-- ============================================================

create table if not exists property_classification_mart.place_classification_scores (
    poi_id varchar not null,
    place_name varchar,

    candidate_category varchar not null,
    candidate_subcategory varchar not null,
    candidate_detail_level_3 varchar not null,

    classification_score integer,
    matched_keyword_count integer,
    source_field_count integer,
    matched_keywords varchar,
    highest_priority integer,

    created_at timestamp default current_timestamp,

    primary key (poi_id, candidate_category, candidate_subcategory, candidate_detail_level_3)
);

create index if not exists idx_place_classification_scores_place
    on property_classification_mart.place_classification_scores(poi_id);

-- ============================================================
-- 8. Classification recommendations
-- One row per place with the top recommended classification.
-- ============================================================

create table if not exists property_classification_mart.place_classification_recommendations (
    poi_id varchar not null,
    place_name varchar,

    current_category varchar,
    current_subcategory varchar,
    current_detail_level_3 varchar,

    recommended_category varchar,
    recommended_subcategory varchar,
    recommended_detail_level_3 varchar,

    classification_score integer,
    runner_up_score integer,
    score_margin integer,
    matched_keyword_count integer,
    matched_keywords varchar,
    classification_confidence varchar,
    recommendation_rank integer default 1,

    created_at timestamp default current_timestamp,

    primary key (poi_id)
);

-- ============================================================
-- 9. Classification review queue
-- Manual review table for low confidence, mixed, missing, or changed classifications.
-- ============================================================

create table if not exists property_classification_mart.place_classification_review_queue (
    poi_id varchar not null,
    place_name varchar,

    current_category varchar,
    current_subcategory varchar,
    current_detail_level_3 varchar,

    recommended_category varchar,
    recommended_subcategory varchar,
    recommended_detail_level_3 varchar,

    classification_confidence varchar,
    classification_score integer,
    score_margin integer,
    matched_keywords varchar,
    classification_text_raw varchar,

    review_reason varchar,
    review_status varchar default 'needs_review',

    reviewed_category varchar,
    reviewed_subcategory varchar,
    reviewed_detail_level_3 varchar,
    review_notes varchar,

    created_at timestamp default current_timestamp,
    reviewed_at timestamp,

    primary key (poi_id)
);

-- ============================================================
-- 10. Classification overrides
-- Durable manual override table.
-- This table should not be rebuilt each run.
-- Manual overrides win over automated recommendations.
-- ============================================================

create table if not exists property_classification_mart.place_classification_overrides (
    poi_id varchar not null,

    override_category varchar,
    override_subcategory varchar,
    override_detail_level_3 varchar,

    override_reason varchar,
    reviewed_by varchar,
    active_flag boolean default true,

    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp,

    primary key (poi_id)
);

-- ============================================================
-- 11. Final classified places
-- Final output table for app and downstream use.
-- This table joins source curated places to recommendations and overrides.
-- ============================================================

create table if not exists property_classification_mart.curated_places_classified (
    poi_id varchar not null,
    place_name varchar,

    original_category varchar,
    original_subcategory varchar,
    original_detail_level_3 varchar,

    matched_keywords varchar,

    recommended_category varchar,
    recommended_subcategory varchar,
    recommended_detail_level_3 varchar,

    final_category varchar,
    final_subcategory varchar,
    final_detail_level_3 varchar,

    classification_method varchar,
    classification_confidence varchar,
    classification_score integer,

    classification_run_at timestamp default current_timestamp,

    primary key (poi_id)
);
