"""Neighborhood Explorer Streamlit app for geography and demographic review."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from nyc_property_finder.app.base_map import (
    DEMOGRAPHIC_METRICS,
    BaseMapData,
    build_base_map_deck,
    format_metric_value,
    metric_options,
    prepare_base_map_data,
)
from nyc_property_finder.services.config import PROJECT_ROOT, load_config


st.set_page_config(page_title="Neighborhood Explorer", layout="wide")


@st.cache_data(show_spinner="Loading geography and demographic layers...")
def cached_prepare_base_map_data(
    database_path: str,
    tract_path: str,
    tract_id_col: str,
    metric: str,
) -> BaseMapData:
    """Cached wrapper around base-map assembly."""

    return prepare_base_map_data(
        database_path=database_path,
        tract_path=tract_path,
        tract_id_col=tract_id_col,
        metric=metric,
    )


def _coverage_label(value: float) -> str:
    return f"{value:.1%}"


def _render_data_status(database_path: str, tract_path: str, stats: dict[str, object]) -> None:
    with st.sidebar:
        st.header("Data")
        st.caption(f"Database: `{database_path}`")
        st.caption(f"Tracts: `{tract_path}`")
        st.write(f"Mapping: {'ready' if stats.get('mapping_ready') else 'missing'}")
        st.write(f"Tract features: {'ready' if stats.get('tract_features_ready') else 'missing'}")
        st.write(f"NTA features: {'ready' if stats.get('nta_features_ready') else 'missing'}")

        if not Path(database_path).exists():
            st.error("Database file is missing. Build the gold tables before using this app.")
        if not Path(tract_path).exists():
            st.error("Census tract GeoJSON is missing.")


def _render_summary(map_data: BaseMapData) -> None:
    stats = map_data.stats
    metric_cols = st.columns(4)
    metric_cols[0].metric("Tracts", f"{stats['tract_count']:,}")
    metric_cols[1].metric("Neighborhoods", f"{stats['neighborhood_count']:,}")
    metric_cols[2].metric("Metric rows", f"{stats['metric_non_null_count']:,}")
    metric_cols[3].metric("Metric coverage", _coverage_label(float(stats["metric_coverage"])))

    if stats["metric_non_null_count"] == 0:
        st.warning(
            "The geography foundation is loaded, but the current local demographic feature "
            "tables have no populated values for this metric. Rebuild the Metro Deep Dive "
            "feature tables to turn the map from boundary review into demographic review."
        )


def _render_selected_metric_table(map_data: BaseMapData, layer_mode: str) -> None:
    geography = map_data.neighborhoods if layer_mode == "Neighborhoods" else map_data.tracts
    id_column = "nta_id" if layer_mode == "Neighborhoods" else "tract_id"
    name_columns = ["nta_name", "borough"]
    columns = [id_column, *name_columns, map_data.metric]
    available_columns = [column for column in columns if column in geography.columns]
    table = geography[available_columns].copy()
    table[map_data.metric] = pd.to_numeric(table[map_data.metric], errors="coerce")
    table = table.sort_values(map_data.metric, ascending=False, na_position="last")
    table[map_data.metric] = [
        format_metric_value(value, map_data.metric)
        for value in table[map_data.metric]
    ]
    table = table.rename(
        columns={
            id_column: "ID",
            "nta_name": "Neighborhood",
            "borough": "Borough",
            map_data.metric: DEMOGRAPHIC_METRICS[map_data.metric]["label"],
        }
    )
    st.dataframe(table.head(25), use_container_width=True, hide_index=True)


def main() -> None:
    """Render the Neighborhood Explorer application."""

    config = load_config()
    settings = config["settings"]
    data_sources = config["data_sources"]["sources"]
    database_path = str(PROJECT_ROOT / settings["database_path"])
    tract_source = data_sources["census_tracts"]
    tract_path = str(PROJECT_ROOT / tract_source["path"])
    tract_id_col = tract_source.get("id_column", "GEOID")
    center = settings.get("default_map_center", {"lat": 40.7128, "lon": -74.0060})

    st.title("Neighborhood Explorer")
    st.caption(
        "Reusable Brooklyn and Manhattan tract/neighborhood context before property-layer work."
    )

    with st.sidebar:
        st.header("Map")
        metric_labels = metric_options()
        selected_label = st.selectbox(
            "Demographic metric",
            list(metric_labels.values()),
            index=0,
        )
        metric = next(key for key, label in metric_labels.items() if label == selected_label)
        layer_mode = st.segmented_control(
            "Geography",
            ["Tracts", "Neighborhoods"],
            default="Tracts",
        )

    map_data = cached_prepare_base_map_data(
        database_path=database_path,
        tract_path=tract_path,
        tract_id_col=tract_id_col,
        metric=metric,
    )
    _render_data_status(database_path, tract_path, map_data.stats)
    _render_summary(map_data)

    st.pydeck_chart(
        build_base_map_deck(
            map_data,
            layer_mode=layer_mode,
            center_lat=float(center["lat"]),
            center_lon=float(center["lon"]),
            zoom=int(settings.get("default_map_zoom", 10)),
        ),
        use_container_width=True,
    )

    st.subheader(f"{layer_mode} by {metric_labels[metric]}")
    _render_selected_metric_table(map_data, layer_mode)


if __name__ == "__main__":
    main()
