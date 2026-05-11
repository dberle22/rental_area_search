-- Neighborhood Character V1 validation queries
--
-- Purpose:
-- Validate that Explore MVP rankings and "known for" outputs broadly match
-- expected NYC neighborhood intuition before the app surface is built.
--
-- Expected inputs:
-- neighborhood_character_mart.nta_category_density
-- neighborhood_character_mart.nta_character_profile
-- neighborhood_character_mart.nta_category_controls

-- 1. Top neighborhoods for each enabled Explore category.
with enabled_categories as (
    select
        category,
        include_in_explore_v1,
        known_for_enabled
    from neighborhood_character_mart.nta_category_controls
    where include_in_explore_v1 = true
),
ranked as (
    select
        d.category,
        d.nta_name,
        d.borough,
        d.poi_count,
        d.nyc_percentile,
        d.concentration_tier,
        d.meets_evidence_threshold,
        row_number() over (
            partition by d.category
            order by
                d.poi_count desc,
                coalesce(d.subcategory_diversity, 0) desc,
                d.nta_name asc
        ) as rank_in_category
    from neighborhood_character_mart.nta_category_density d
    inner join enabled_categories c
        on d.category = c.category
    where d.source = 'curated'
)
select
    category,
    rank_in_category,
    nta_name,
    borough,
    poi_count,
    nyc_percentile,
    concentration_tier,
    meets_evidence_threshold
from ranked
where rank_in_category <= 10
order by category, rank_in_category;

-- 2. Known neighborhood expectation check.
--
-- Edit the rows below as the validation set evolves.
with expected_pairs as (
    select 'Williamsburg' as nta_name, 'bars' as category union all
    select 'Greenwich Village' as nta_name, 'bookstores' as category union all
    select 'Lower East Side' as nta_name, 'music_venues' as category union all
    select 'Chelsea' as nta_name, 'museums' as category union all
    select 'Midtown' as nta_name, 'hotels' as category
),
observed as (
    select
        d.nta_name,
        d.category,
        d.poi_count,
        d.nyc_percentile,
        d.concentration_tier,
        row_number() over (
            partition by d.category
            order by
                d.poi_count desc,
                coalesce(d.subcategory_diversity, 0) desc,
                d.nta_name asc
        ) as rank_in_category
    from neighborhood_character_mart.nta_category_density d
    where d.source = 'curated'
)
select
    e.nta_name,
    e.category,
    o.rank_in_category,
    o.poi_count,
    o.nyc_percentile,
    o.concentration_tier
from expected_pairs e
left join observed o
    on e.nta_name = o.nta_name
   and e.category = o.category
order by e.category, e.nta_name;

-- 3. Character profile spot check for neighborhoods the app will feature.
select
    nta_name,
    borough,
    total_curated_poi_count,
    destination_categories,
    strong_categories,
    top_category,
    top_subcategory
from neighborhood_character_mart.nta_character_profile
where nta_name in (
    'Williamsburg',
    'Greenwich Village',
    'Lower East Side',
    'Chelsea',
    'Midtown'
)
order by nta_name;
