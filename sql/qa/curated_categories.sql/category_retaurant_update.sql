-- Review the classification mart outputs for mixed_restaurants.
-- This QA file is for analyst inspection, not production classification logic.

select
    poi_id,
    place_name,
    original_subcategory,
    recommended_subcategory,
    recommended_detail_level_3,
    final_subcategory,
    final_detail_level_3,
    classification_method,
    classification_confidence,
    classification_score,
    matched_keywords
from property_classification_mart.curated_places_classified
where original_category = 'restaurants'
  and original_subcategory = 'mixed_restaurants'
order by
    classification_confidence,
    classification_score desc,
    place_name;

select
    recommended_subcategory,
    recommended_detail_level_3,
    classification_confidence,
    count(*) as poi_count
from property_classification_mart.place_classification_recommendations
where current_category = 'restaurants'
  and current_subcategory = 'mixed_restaurants'
group by all
order by poi_count desc, recommended_subcategory, recommended_detail_level_3;
