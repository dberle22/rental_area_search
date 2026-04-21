"""Resolve Takeout source rows to Google place IDs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from nyc_property_finder.google_places_poi.cache import (
    RESOLUTION_CACHE_COLUMNS,
    merge_resolution_cache,
    read_resolution_cache,
    write_resolution_cache,
)
from nyc_property_finder.google_places_poi.client import search_text_place_id
from nyc_property_finder.google_places_poi.config import (
    DEFAULT_API_KEYS_PATH,
    DEFAULT_ENV_PATH,
    DEFAULT_MAX_TEXT_SEARCH_CALLS,
    DEFAULT_RESOLUTION_CACHE_PATH,
    DEFAULT_SEARCH_CONTEXT,
    get_google_maps_api_key,
)
from nyc_property_finder.google_places_poi.parse_takeout import parse_google_places_saved_list_csv


ResolutionFetcher = Callable[[str, str], dict[str, Any]]


@dataclass(frozen=True)
class ResolveReport:
    """Summary of one guarded resolve-only run."""

    input_path: str
    resolution_cache_path: str
    parsed_rows: int
    input_cache_hits: int
    existing_resolved_cache_rows: int
    attempted_text_search_calls: int
    max_text_search_calls: int
    resolved: int
    no_match: int

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict for logging, notebooks, or future CLI output."""

        return asdict(self)


def resolve_place_ids(
    csv_path: str | Path,
    api_key: str | None = None,
    resolution_cache_path: str | Path = DEFAULT_RESOLUTION_CACHE_PATH,
    search_context: str = DEFAULT_SEARCH_CONTEXT,
    max_text_search_calls: int = DEFAULT_MAX_TEXT_SEARCH_CALLS,
    env_path: str | Path = DEFAULT_ENV_PATH,
    api_keys_path: str | Path = DEFAULT_API_KEYS_PATH,
    fetcher: ResolutionFetcher = search_text_place_id,
) -> ResolveReport:
    """Resolve uncached saved-list rows to Google place IDs with a hard call cap."""

    csv_path = Path(csv_path)
    api_key = api_key or get_google_maps_api_key(env_path=env_path, api_keys_path=api_keys_path)
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY is required for resolve_place_ids.")

    parsed = parse_google_places_saved_list_csv(csv_path, search_context=search_context)
    cache = read_resolution_cache(resolution_cache_path)
    cache = _refresh_cache_source_metadata(cache, parsed)

    cached_source_ids = set(cache.loc[cache["google_place_id"] != "", "source_record_id"])
    parsed_source_ids = set(parsed["source_record_id"])
    input_cached_source_ids = parsed_source_ids & cached_source_ids
    unresolved = parsed[~parsed["source_record_id"].isin(cached_source_ids)].copy()

    if len(unresolved) > max_text_search_calls:
        raise ValueError(
            "Resolve run would exceed max_text_search_calls: "
            f"{len(unresolved)} needed, cap is {max_text_search_calls}."
        )

    new_rows: list[dict[str, str]] = []
    for row in unresolved.to_dict("records"):
        # The fetcher only sees the query and key. Tests can inject a fake
        # fetcher, while production uses the ID-only Google Text Search client.
        result = fetcher(row["search_query"], api_key)
        new_rows.append(_build_resolution_cache_row(row, result))

        # Write after every successful request so an interrupted run keeps the
        # calls it already paid for.
        merged_cache = merge_resolution_cache(cache, pd.DataFrame(new_rows))
        write_resolution_cache(merged_cache, resolution_cache_path)

    new_cache_rows = pd.DataFrame(new_rows, columns=RESOLUTION_CACHE_COLUMNS)
    if new_rows or not cache.empty:
        write_resolution_cache(merge_resolution_cache(cache, new_cache_rows), resolution_cache_path)
    resolved = int((new_cache_rows.get("google_place_id", pd.Series(dtype=str)) != "").sum())
    no_match = int((new_cache_rows.get("match_status", pd.Series(dtype=str)) == "no_match").sum())

    return ResolveReport(
        input_path=str(csv_path),
        resolution_cache_path=str(resolution_cache_path),
        parsed_rows=len(parsed),
        input_cache_hits=len(input_cached_source_ids),
        existing_resolved_cache_rows=len(cached_source_ids),
        attempted_text_search_calls=len(unresolved),
        max_text_search_calls=max_text_search_calls,
        resolved=resolved,
        no_match=no_match,
    )


def _build_resolution_cache_row(source_row: dict[str, Any], result: dict[str, Any]) -> dict[str, str]:
    # Keep the cache human-reviewable: source fields sit next to the matched
    # Google ID and status.
    google_place_id = str(result.get("google_place_id", "") or "")
    match_status = str(result.get("match_status", "top_candidate" if google_place_id else "no_match"))
    return {
        "source_record_id": str(source_row.get("source_record_id", "")),
        "source_system": str(source_row.get("source_system", "")),
        "source_file": str(source_row.get("source_file", "")),
        "source_list_name": str(source_row.get("source_list_name", "")),
        "category": str(source_row.get("category", "")),
        "input_title": str(source_row.get("input_title", "")),
        "note": str(source_row.get("note", "")),
        "tags": str(source_row.get("tags", "")),
        "comment": str(source_row.get("comment", "")),
        "source_url": str(source_row.get("source_url", "")),
        "search_query": str(source_row.get("search_query", "")),
        "google_place_id": google_place_id,
        "match_status": match_status,
    }


def _refresh_cache_source_metadata(cache: pd.DataFrame, parsed: pd.DataFrame) -> pd.DataFrame:
    """Fill source metadata columns in older cache rows without new API calls."""

    if cache.empty:
        return cache

    metadata_columns = [
        "source_system",
        "source_file",
        "source_list_name",
        "category",
        "input_title",
        "note",
        "tags",
        "comment",
        "source_url",
        "search_query",
    ]
    parsed_metadata = parsed.set_index("source_record_id")
    output = cache.copy()
    for index, row in output.iterrows():
        source_record_id = row["source_record_id"]
        if source_record_id not in parsed_metadata.index:
            continue
        for column in metadata_columns:
            if not str(output.at[index, column]).strip():
                output.at[index, column] = str(parsed_metadata.at[source_record_id, column])
    return output
