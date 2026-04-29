"""Neighborhood Explorer Streamlit app for geography and demographic review."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from nyc_property_finder.app.base_map import (
    DEFAULT_PUBLIC_POI_CATEGORIES,
    DEFAULT_PUBLIC_POI_SELECTION,
    DEMOGRAPHIC_METRICS,
    BaseGeographyData,
    BaseMapData,
    PoiMapData,
    available_poi_source_lists,
    build_base_map_data_from_loaded,
    build_base_map_deck,
    filter_poi_points_by_source_lists,
    filter_points_to_supported_geography,
    filter_public_poi_points_by_categories,
    format_metric_value,
    load_base_geography_data,
    load_poi_map_data,
    load_public_poi_map_data,
    metric_options,
)
from nyc_property_finder.services.config import PROJECT_ROOT, load_config


st.set_page_config(page_title="Neighborhood Explorer", layout="wide")


@st.cache_data(show_spinner="Loading geography and demographic layers...")
def cached_load_base_geography_data(
    database_path: str,
    tract_path: str,
    tract_id_col: str,
 ) -> BaseGeographyData:
    """Cached wrapper around metric-independent geography assembly."""

    return load_base_geography_data(
        database_path=database_path,
        tract_path=tract_path,
        tract_id_col=tract_id_col,
    )


@st.cache_data(show_spinner="Loading points of interest...")
def cached_load_poi_map_data(database_path: str) -> PoiMapData:
    """Cached wrapper around POI map-layer assembly."""

    return load_poi_map_data(database_path=database_path)


@st.cache_data(show_spinner="Loading public baseline POIs...")
def cached_load_public_poi_map_data(
    database_path: str,
    selected_categories: tuple[str, ...],
) -> PoiMapData:
    """Cached wrapper around public baseline POI loading."""

    return load_public_poi_map_data(
        database_path=database_path,
        selected_categories=selected_categories,
    )


def _render_selected_metric_table(map_data: BaseMapData, layer_mode: str) -> None:
    geography = map_data.neighborhoods if layer_mode == "Neighborhoods" else map_data.tracts
    id_column = "nta_id" if layer_mode == "Neighborhoods" else "tract_id"
    name_columns = ["nta_name", "borough"]
    metric_columns = list(DEMOGRAPHIC_METRICS.keys())
    columns = [id_column, *name_columns, *metric_columns]
    available_columns = [column for column in columns if column in geography.columns]
    table = geography[available_columns].copy()
    if map_data.metric in table.columns:
        table[map_data.metric] = pd.to_numeric(table[map_data.metric], errors="coerce")
        table = table.sort_values(map_data.metric, ascending=False, na_position="last")
    for metric in metric_columns:
        if metric in table.columns:
            numeric = pd.to_numeric(table[metric], errors="coerce")
            table[metric] = [format_metric_value(value, metric) for value in numeric]
    table = table.rename(
        columns={
            id_column: "ID",
            "nta_name": "Neighborhood",
            "borough": "Borough",
            **{
                metric: metadata["label"]
                for metric, metadata in DEMOGRAPHIC_METRICS.items()
            },
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
    st.caption("Explore NYC neighborhood demographics and curated/public place context.")
    st.markdown(
        "Start with **Neighborhoods** for broader comparisons, switch to **Tracts** for finer detail, "
        "hover any polygon to see demographics and POI counts, and turn on **Public POIs** when you "
        "want baseline city infrastructure layered on top of your curated places."
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
            default="Neighborhoods",
        )
        show_demographics = st.toggle("Show demographic colors", value=True)

    geography_data = cached_load_base_geography_data(
        database_path=database_path,
        tract_path=tract_path,
        tract_id_col=tract_id_col,
    )
    map_data = build_base_map_data_from_loaded(geography_data, metric=metric)
    poi_data = cached_load_poi_map_data(database_path)
    poi_source_lists = available_poi_source_lists(poi_data.points)
    public_poi_categories = list(DEFAULT_PUBLIC_POI_CATEGORIES)

    with st.sidebar:
        st.header("Curated POIs")
        show_pois = st.toggle("Show curated layer", value=not poi_data.points.empty)
        selected_poi_source_lists = st.multiselect(
            "Curated lists",
            poi_source_lists,
            default=poi_source_lists,
            disabled=not show_pois or poi_data.points.empty,
        )
        if poi_data.points.empty:
            st.caption("No curated POIs with coordinates are available yet.")
        elif show_pois:
            st.caption(f"{len(poi_data.points):,} curated POIs loaded from {poi_data.source}.")

        st.header("Public POIs")
        show_public_pois = st.toggle(
            "Show public layer",
            value=False,
        )
        selected_public_poi_categories = st.multiselect(
            "Public categories",
            public_poi_categories,
            default=list(DEFAULT_PUBLIC_POI_SELECTION),
            disabled=not show_public_pois,
            format_func=lambda value: value.replace("_", " ").title(),
        )

    public_poi_data = (
        cached_load_public_poi_map_data(
            database_path,
            tuple(selected_public_poi_categories),
        )
        if show_public_pois and selected_public_poi_categories
        else PoiMapData(
            points=pd.DataFrame(),
            source="not_loaded",
            stats={"poi_count": 0, "category_count": 0, "configured_category_count": 0},
        )
    )

    with st.sidebar:
        if show_public_pois and not selected_public_poi_categories:
            st.caption("Choose at least one public category to load public POIs.")
        elif show_public_pois and public_poi_data.points.empty:
            st.caption("No public baseline POIs are available for the selected public categories.")
        elif show_public_pois:
            st.caption(
                f"{len(public_poi_data.points):,} public POIs loaded across "
                f"{public_poi_data.stats['category_count']} selected categories."
            )

    filtered_poi_points = filter_poi_points_by_source_lists(
        poi_data.points,
        tuple(selected_poi_source_lists),
    )
    filtered_public_poi_points = filter_public_poi_points_by_categories(
        public_poi_data.points,
        tuple(selected_public_poi_categories),
    )
    filtered_poi_points = filter_points_to_supported_geography(filtered_poi_points, map_data.tracts)
    filtered_public_poi_points = filter_points_to_supported_geography(
        filtered_public_poi_points,
        map_data.tracts,
    )

    st.pydeck_chart(
        build_base_map_deck(
            map_data,
            layer_mode=layer_mode,
            show_demographics=show_demographics,
            poi_points=filtered_poi_points,
            show_pois=show_pois,
            public_poi_points=filtered_public_poi_points,
            show_public_pois=show_public_pois,
            center_lat=float(center["lat"]),
            center_lon=float(center["lon"]),
            zoom=int(settings.get("default_map_zoom", 10)),
        ),
        use_container_width=True,
    )

    if show_pois and not poi_data.points.empty:
        st.caption(
            f"Showing {len(filtered_poi_points):,} of {len(poi_data.points):,} curated POIs "
            "for the selected list filters."
        )
    if show_public_pois and not public_poi_data.points.empty:
        st.caption(
            f"Showing {len(filtered_public_poi_points):,} of "
            f"{len(public_poi_data.points):,} public POIs for the selected category filters."
        )

    if show_demographics:
        st.subheader(f"{layer_mode} by {metric_labels[metric]}")
    else:
        st.subheader(f"{layer_mode} data table ({metric_labels[metric]})")
        st.caption("Demographic map colors are hidden; NTA boundaries remain visible.")
    _render_selected_metric_table(map_data, layer_mode)


if __name__ == "__main__":
    main()
