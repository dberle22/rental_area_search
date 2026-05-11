# Sprint 3 Stoop Explore Foundation Audit

Last updated: 2026-05-10

## Purpose

This note records the first Sprint 3 audit of the current Neighborhood Explorer
surface before layering in Stoop Explore intelligence.

The goal is not to redesign the app from scratch. The goal is to keep the parts
that already make the map useful, remove or de-emphasize the parts that feel
like internal QA, and create a cleaner foundation for the "where should I spend
a day?" product frame.

## Keep

- The five-borough geography foundation in `app/streamlit_app_v2.py` and
  `src/nyc_property_finder/app/base_map.py`.
- Neighborhood-first default map mode. It already matches the Explore product
  better than tract-first analysis.
- Curated POI overlay as a first-class layer.
- Public baseline POI overlay as optional supporting context.
- Honest missing-data behavior for demographic metrics.
- The sortable table under the map as a secondary inspection surface.

## De-emphasize

- The "demographic review" framing. It should become supporting context, not
  the app's headline story.
- Tract mode as a default starting point. It remains useful, but it should feel
  secondary to neighborhood exploration.
- QA-style language around data loading. Useful for build/debug, but not the
  front-door product voice.

## Remove From The Main Story

- Neighborhood Explorer naming.
- Property Explorer carryover language where it still leaks into supporting app
  or project copy.
- Any implication that the app's main job is general-purpose POI browsing
  rather than helping someone choose a neighborhood for a specific kind of day.

## Foundation Direction

The Stoop Explore foundation should keep the existing map and layer controls,
but reframe them around three ideas:

1. Start with a neighborhood, not a tract.
2. Use curated places as the primary Explore signal.
3. Read category rankings and "known for" signals from the precomputed
   `neighborhood_character_mart`, not ad hoc runtime analysis.

## Immediate Build Implications

- Add a durable entry point at `app/stoop_explore.py`.
- Keep `app/streamlit_app_v2.py` as a compatibility path during transition.
- Rebrand visible page copy to Stoop Explore.
- Add a lightweight app-side reader for:
  - `neighborhood_character_mart.nta_category_controls`
  - `neighborhood_character_mart.nta_category_density`
  - `neighborhood_character_mart.nta_character_profile`

## Deferred Until UI Lock

These decisions need explicit product signoff before the app surface is fully
wired:

- Whether `Top neighborhoods for X` lives above the map, in the sidebar, or in
  a right-hand panel.
- Whether the first-load default category should be `restaurants`, `shopping`,
  or `hotels`.
- Whether the selected NTA should come primarily from map hover/click, sidebar
  search, or the ranking panel.
