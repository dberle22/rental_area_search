-- Explore where we have Tract data

-- Check coverage in Staging
select state,
	-- year,
	count(*) as total_tracts,
	count(distinct GEOID) as distinct_tracts
from staging.acs_age_tract
group by all;

-- Check coverage in Silver
	-- Tract exists
select geo_level,
	count(*) as total_records
from gold.affordability_wide
where geo_level = 'tract'
group by all

-- Check tract states
	-- We only have SC, FL, GA, NC and some weird nulls
		-- The NULLs all have 0 population
with base as (
select geo_level,
	geo_id,
	state_fip,
	state_name,
	county_name,
	geo_name
from gold.affordability_wide kpi
left join silver.xwalk_tract_county cty
	on kpi.geo_id = cty.tract_geoid
where kpi.geo_level = 'tract'
and kpi.year = '2024'
)

select geo_level,
	state_name,
	count(*) as total_records
from base 
group by all