"""High-level Google Places POI v2 pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from nyc_property_finder.google_places_poi.build_dim import build_dim_user_poi_v2
from nyc_property_finder.google_places_poi.config import (
    DEFAULT_DETAILS_CACHE_PATH,
    DEFAULT_MAX_DETAILS_CALLS,
    DEFAULT_MAX_TEXT_SEARCH_CALLS,
    DEFAULT_RESOLUTION_CACHE_PATH,
    DEFAULT_SEARCH_CONTEXT,
)
from nyc_property_finder.google_places_poi.enrich import EnrichReport, enrich_place_details
from nyc_property_finder.google_places_poi.resolve import ResolveReport, resolve_place_ids
from nyc_property_finder.google_places_poi.summary import (
    DEFAULT_QA_PATH,
    DEFAULT_SUMMARY_PATH,
    build_summary,
    write_qa_csv,
    write_summary,
)
from nyc_property_finder.services.config import load_config
from nyc_property_finder.services.duckdb_service import DuckDBService


@dataclass(frozen=True)
class GooglePlacesPoiPipelineReport:
    """Summary of a complete Google Places POI v2 pipeline run."""

    resolve: ResolveReport
    enrich: EnrichReport
    dim_rows: int
    dim_with_coordinates: int
    database_path: str | None
    table_name: str
    summary_path: str
    qa_path: str
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict for logging, notebooks, or future CLI output."""

        output = asdict(self)
        output["resolve"] = self.resolve.to_dict()
        output["enrich"] = self.enrich.to_dict()
        return output


def run(
    csv_path: str | Path,
    database_path: str | Path | None = None,
    resolution_cache_path: str | Path = DEFAULT_RESOLUTION_CACHE_PATH,
    details_cache_path: str | Path = DEFAULT_DETAILS_CACHE_PATH,
    search_context: str = DEFAULT_SEARCH_CONTEXT,
    max_text_search_calls: int = DEFAULT_MAX_TEXT_SEARCH_CALLS,
    max_details_calls: int = DEFAULT_MAX_DETAILS_CALLS,
    api_key: str | None = None,
    write_database: bool = True,
    table_name: str = "dim_user_poi_v2",
    schema: str = "property_explorer_gold",
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
    qa_path: str | Path = DEFAULT_QA_PATH,
) -> GooglePlacesPoiPipelineReport:
    """Resolve, enrich, build, and optionally write dim_user_poi_v2."""

    resolve_report = resolve_place_ids(
        csv_path=csv_path,
        resolution_cache_path=resolution_cache_path,
        search_context=search_context,
        max_text_search_calls=max_text_search_calls,
        api_key=api_key,
    )
    enrich_report = enrich_place_details(
        resolution_cache_path=resolution_cache_path,
        details_cache_path=details_cache_path,
        max_details_calls=max_details_calls,
        api_key=api_key,
    )
    dim_user_poi = build_dim_user_poi_v2(
        resolution_cache_path=resolution_cache_path,
        details_cache_path=details_cache_path,
    )

    resolved_database_path = str(database_path) if database_path is not None else None
    if write_database:
        if database_path is None:
            database_path = load_config()["settings"]["database_path"]
        resolved_database_path = str(database_path)
        # Keep this write isolated to the v2 table so the existing app-facing
        # dim_user_poi table remains untouched.
        with DuckDBService(database_path) as duckdb_service:
            duckdb_service.write_dataframe(
                dim_user_poi,
                table_name=table_name,
                schema=schema,
                if_exists="replace",
            )

    summary = build_summary(
        resolution_cache_path=resolution_cache_path,
        details_cache_path=details_cache_path,
    )
    write_summary(summary, summary_path)
    write_qa_csv(
        resolution_cache_path=resolution_cache_path,
        details_cache_path=details_cache_path,
        path=qa_path,
    )

    return GooglePlacesPoiPipelineReport(
        resolve=resolve_report,
        enrich=enrich_report,
        dim_rows=len(dim_user_poi),
        dim_with_coordinates=int(dim_user_poi[["lat", "lon"]].notna().all(axis=1).sum()),
        database_path=resolved_database_path,
        table_name=f"{schema}.{table_name}",
        summary_path=str(summary_path),
        qa_path=str(qa_path),
        summary=summary,
    )
