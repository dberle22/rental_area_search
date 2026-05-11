# Post-MVP Improvements

This doc holds ideas that are useful, but not needed for the first local MVP.
Keeping them here helps the Sprint 1 contracts stay lean without losing good
future product hooks.

## Listing Experience

- Add listing images or a media table sourced from `image_url` or future listing
  adapters.
- Add richer listing history with snapshots for price changes, stale listings,
  and removed listings.
- Add an optional Google Places API resolver for Google Maps saved-list CSV
  exports. The MVP uses NYC GeoSearch against place names and quarantines misses;
  a later Places API path would use a restricted `GOOGLE_MAPS_API_KEY`, official
  Text Search or Place Details calls, and persisted place IDs.
- Add days-on-market once scraper or adapter data makes listing freshness easy
  to maintain.
- Add amenity parsing into a bridge table for better filters and comparison.
- Add source-specific adapters for StreetEasy, Zillow, RentHop, or broker feeds
  after access, terms, and data stability are understood.

## POI And Lifestyle Fit

- Add manual POI category overrides when keyword categories are not precise
  enough.
- Add list-level weighting, for example Restaurants matter differently than
  Museums or Bookstores.
- Support multiple user POI profiles and compare how rankings change by user.

## Distance And Mobility

- Replace straight-line distance with walking-time or network-distance proxies.
- Consider NYC Geoclient/Geoservice if official address matching, BBL/BIN, or
  additional geography attributes become useful.
- Add commute anchors and travel-time scoring to work, friends, frequent places,
  or transit hubs.
- Add subway service frequency or reliability context once core station distance
  works.

## Users And Shortlists

- Replace the local default user with app-entered user names.
- Add multiple shortlists per user, such as `tour`, `maybe`, `offer`, or
  `rejected`.
- Add historical notes/events if a single current shortlist row becomes too
  limiting.

## Neighborhood Context

- Add crime/safety only after a careful source and framing decision.
- Add schools, flood risk, 311, noise, and other neighborhood context once the
  basic feature pipeline is stable.
- Add better tract-to-neighborhood diagnostics and alternate neighborhood
  definitions beyond NTAs.
