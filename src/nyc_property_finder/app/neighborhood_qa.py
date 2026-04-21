"""QA helpers for neighborhood geography and demographic data coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from nyc_property_finder.app.base_map import (
    DEMOGRAPHIC_METRICS,
    NTA_FEATURE_TABLE,
    TRACT_FEATURE_TABLE,
    TRACT_TO_NTA_TABLE,
    load_feature_table,
)
from nyc_property_finder.app.explorer import table_exists
from nyc_property_finder.services.config import PROJECT_ROOT
from nyc_property_finder.services.duckdb_service import DuckDBService


QA_TABLES = {
    "Tract to NTA mapping": TRACT_TO_NTA_TABLE,
    "Tract features": TRACT_FEATURE_TABLE,
    "NTA features": NTA_FEATURE_TABLE,
}


def format_coverage(value: float) -> str:
    """Format a coverage ratio for Streamlit display."""

    return f"{value:.1%}"


def resolve_config_path(path: str | None, project_root: Path = PROJECT_ROOT) -> Path | None:
    """Resolve a possibly relative config path against the project root."""

    if not path:
        return None

    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_root / candidate


def table_row_count(database_path: str | Path, full_table_name: str) -> int | None:
    """Return row count for a DuckDB table, or None when unavailable."""

    if not table_exists(database_path, full_table_name):
        return None

    with DuckDBService(database_path, read_only=True) as duckdb_service:
        result = duckdb_service.query_df(f"SELECT COUNT(*) AS row_count FROM {full_table_name}")
    return int(result["row_count"].iloc[0])


def build_table_status(database_path: str | Path) -> pd.DataFrame:
    """Summarize expected gold tables used by the neighborhood apps."""

    rows = []
    for label, full_table_name in QA_TABLES.items():
        exists = table_exists(database_path, full_table_name)
        rows.append(
            {
                "Area": label,
                "Table": full_table_name,
                "Status": "ready" if exists else "missing",
                "Rows": table_row_count(database_path, full_table_name) if exists else 0,
            }
        )
    return pd.DataFrame(rows)


def build_metric_coverage(database_path: str | Path, grain: str) -> pd.DataFrame:
    """Summarize non-null demographic coverage for tract or NTA feature tables."""

    if grain == "tract":
        table_name = TRACT_FEATURE_TABLE
        id_columns = ["tract_id"]
    elif grain == "nta":
        table_name = NTA_FEATURE_TABLE
        id_columns = ["nta_id", "nta_name"]
    else:
        raise ValueError(f"Unsupported metric coverage grain: {grain}")

    features = load_feature_table(database_path, table_name, id_columns)
    row_count = len(features)
    rows = []
    for metric, metadata in DEMOGRAPHIC_METRICS.items():
        values = pd.to_numeric(features[metric], errors="coerce")
        populated = int(values.notna().sum())
        coverage = float(populated / row_count) if row_count else 0.0
        rows.append(
            {
                "Metric": metadata["label"],
                "Column": metric,
                "Rows": row_count,
                "Populated": populated,
                "Missing": int(row_count - populated),
                "Coverage": coverage,
                "Coverage label": format_coverage(coverage),
            }
        )
    return pd.DataFrame(rows)


def build_source_status(
    data_sources: dict[str, Any],
    project_root: Path = PROJECT_ROOT,
) -> pd.DataFrame:
    """Summarize configured source files and metadata."""

    rows = []
    sources = data_sources.get("sources", {})
    for source_key, source in sources.items():
        if not isinstance(source, dict):
            continue

        resolved_path = resolve_config_path(source.get("path"), project_root)
        alternate_paths = [
            resolve_config_path(path, project_root)
            for path in source.get("alternate_paths", [])
            if resolve_config_path(path, project_root) is not None
        ]
        existing_alternates = [path for path in alternate_paths if path and path.exists()]
        path_exists = bool(resolved_path and resolved_path.exists())
        any_source_exists = path_exists or bool(existing_alternates)
        rows.append(
            {
                "Source": source_key,
                "Status": "ready" if any_source_exists else source.get("status", "missing"),
                "Path": str(resolved_path) if resolved_path else "",
                "Path exists": path_exists,
                "Existing alternate paths": ", ".join(str(path) for path in existing_alternates),
                "Format": source.get("expected_format", ""),
                "Owner": source.get("owner", ""),
                "URL": source.get("source_url", source.get("search_url", "")),
                "Notes": source.get("notes", ""),
            }
        )
    return pd.DataFrame(rows)
