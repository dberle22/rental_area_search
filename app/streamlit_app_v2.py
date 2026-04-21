"""Neighborhood Explorer Streamlit app for geography and demographic review."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from nyc_property_finder.app.base_map import (
    DEMOGRAPHIC_METRICS,
    BaseMapData,
    PoiMapData,
    available_poi_source_lists,
    build_base_map_deck,
    filter_poi_points_by_source_lists,
    format_metric_value,
    load_poi_map_data,
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


@st.cache_data(show_spinner="Loading points of interest...")
def cached_load_poi_map_data(database_path: str) -> PoiMapData:
    """Cached wrapper around POI map-layer assembly."""

    return load_poi_map_data(database_path=database_path)


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
        "Explore Brooklyn and Manhattan neighborhood demographics before property-layer work."
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
            "Demographic geography",
            ["Tracts", "Neighborhoods"],
            default="Tracts",
        )
        show_demographics = st.toggle("Show demographic colors", value=True)

    map_data = cached_prepare_base_map_data(
        database_path=database_path,
        tract_path=tract_path,
        tract_id_col=tract_id_col,
        metric=metric,
    )
    poi_data = cached_load_poi_map_data(database_path)
    poi_source_lists = available_poi_source_lists(poi_data.points)

    with st.sidebar:
        st.header("Points of interest")
        show_pois = st.toggle("Show POIs", value=not poi_data.points.empty)
        selected_poi_source_lists = st.multiselect(
            "POI type",
            poi_source_lists,
            default=poi_source_lists,
            disabled=not show_pois or poi_data.points.empty,
        )
        if poi_data.points.empty:
            st.caption("No POIs with coordinates are available yet.")
        elif show_pois:
            st.caption(f"{len(poi_data.points):,} POIs loaded from {poi_data.source}.")

    filtered_poi_points = filter_poi_points_by_source_lists(
        poi_data.points,
        tuple(selected_poi_source_lists),
    )

    st.pydeck_chart(
        build_base_map_deck(
            map_data,
            layer_mode=layer_mode,
            show_demographics=show_demographics,
            poi_points=filtered_poi_points,
            show_pois=show_pois,
            center_lat=float(center["lat"]),
            center_lon=float(center["lon"]),
            zoom=int(settings.get("default_map_zoom", 10)),
        ),
        use_container_width=True,
    )

    if show_pois and not poi_data.points.empty:
        st.caption(
            f"Showing {len(filtered_poi_points):,} of {len(poi_data.points):,} POIs "
            "for the selected type filters."
        )

    if show_demographics:
        st.subheader(f"{layer_mode} by {metric_labels[metric]}")
    else:
        st.subheader(f"{layer_mode} data table ({metric_labels[metric]})")
        st.caption("Demographic map colors are hidden; NTA boundaries remain visible.")
    _render_selected_metric_table(map_data, layer_mode)


if __name__ == "__main__":
    main()
