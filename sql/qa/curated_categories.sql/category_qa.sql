-- Category Details
select
    category,
    subcategory,
    detail_level_3,
    count(poi_id) as pois
from property_explorer_gold.dim_user_poi_v2
group by all
order by category;

-- Current mixed_restaurants source rows
select
    poi_id,
    source_list_names,
    category,
    subcategory,
    detail_level_3,
    name,
    comment,
    editorial_summary
from property_explorer_gold.dim_user_poi_v2
where category = 'restaurants'
  and subcategory = 'mixed_restaurants';

-- Classification mart QA summaries
select
    classification_method,
    classification_confidence,
    count(*) as poi_count
from property_classification_mart.curated_places_classified
where original_category = 'restaurants'
group by all
order by classification_method, classification_confidence;

select
    review_reason,
    count(*) as poi_count
from property_classification_mart.place_classification_review_queue
group by review_reason
order by poi_count desc, review_reason;

-- Raw Classification review
select recommended_subcategory,
	count(*) as pois 
from property_classification_mart.curated_places_classified
where original_category = 'restaurants'
group by all;

select *
from property_classification_mart.curated_places_classified
where original_category = 'restaurants'
and recommended_subcategory  is null
and original_subcategory = 'mixed_restaurants'
group by all;

select
    c.poi_id,
    c.place_name,
    c.original_category,
    c.original_subcategory,
    c.original_detail_level_3,
    c.recommended_subcategory,
    c.recommended_detail_level_3,
    c.classification_confidence,
    c.classification_score,
    c.matched_keywords,
    t.comment_raw,
    t.editorial_summary_raw,
    t.source_list_names_raw,
    t.tags_raw
from property_classification_mart.curated_places_classified c
left join property_classification_mart.place_classification_text t
    on c.poi_id = t.poi_id
where c.original_category = 'restaurants'
  and c.original_subcategory = 'mixed_restaurants'
  and c.final_subcategory = 'mixed_restaurants'
order by c.place_name;
