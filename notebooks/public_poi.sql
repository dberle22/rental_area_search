SELECT category,
	subcategory,
	count(*) as total_records
FROM property_explorer_gold.dim_public_poi
group by all 
order by category, total_records desc