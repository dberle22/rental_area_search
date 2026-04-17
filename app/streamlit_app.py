"""Minimal Streamlit map explorer."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from nyc_property_finder.services.config import PROJECT_ROOT, load_config
from nyc_property_finder.services.duckdb_service import DuckDBService


st.set_page_config(page_title="NYC Property Finder", layout="wide")


@st.cache_data
def load_table(database_path: str, table_name: str) -> pd.DataFrame:
    """Load a DuckDB table if it exists; otherwise return an empty DataFrame."""

    db_path = Path(database_path)
    if not db_path.exists():
        return pd.DataFrame()

    with DuckDBService(db_path, read_only=True) as duckdb_service:
        try:
            return duckdb_service.query_df(f"SELECT * FROM {table_name}")
        except Exception:
            return pd.DataFrame()


def point_layer(dataframe: pd.DataFrame, color: list[int], radius: int, tooltip_label: str) -> pdk.Layer | None:
    """Create a PyDeck point layer from lon/lat records."""

    if dataframe.empty or not {"lat", "lon"}.issubset(dataframe.columns):
        return None

    return pdk.Layer(
        "ScatterplotLayer",
        data=dataframe.dropna(subset=["lat", "lon"]),
        get_position="[lon, lat]",
        get_fill_color=color,
        get_radius=radius,
        pickable=True,
        auto_highlight=True,
    )


def build_map(properties: pd.DataFrame, poi: pd.DataFrame, center_lat: float, center_lon: float, zoom: int) -> pdk.Deck:
    """Build the property and POI map."""

    layers = [
        layer
        for layer in [
            point_layer(poi, color=[51, 136, 255, 180], radius=45, tooltip_label="POI"),
            point_layer(properties, color=[235, 87, 87, 200], radius=65, tooltip_label="Property"),
        ]
        if layer is not None
    ]

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom, pitch=0)
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="light",
        tooltip={"text": "{name}\n{address}\n{category}"},
    )


def main() -> None:
    """Render the Streamlit app."""

    config = load_config()
    settings = config["settings"]
    database_path = str(PROJECT_ROOT / settings["database_path"])
    center = settings["default_map_center"]

    properties = load_table(database_path, "gold.dim_property_listing")
    poi = load_table(database_path, "gold.dim_user_poi")

    st.title("NYC Property Finder")

    with st.sidebar:
        st.header("Filters")
        max_price = st.number_input("Max price", min_value=0, value=6000, step=250)
        min_beds = st.number_input("Min beds", min_value=0.0, value=0.0, step=0.5)
        selected_categories = []
        if not poi.empty and "category" in poi.columns:
            selected_categories = st.multiselect(
                "POI categories",
                sorted(poi["category"].dropna().unique()),
                default=sorted(poi["category"].dropna().unique()),
            )

    filtered_properties = properties.copy()
    if not filtered_properties.empty:
        if "price" in filtered_properties.columns:
            filtered_properties = filtered_properties[filtered_properties["price"].fillna(0) <= max_price]
        if "beds" in filtered_properties.columns:
            filtered_properties = filtered_properties[filtered_properties["beds"].fillna(0) >= min_beds]

    filtered_poi = poi.copy()
    if selected_categories:
        filtered_poi = filtered_poi[filtered_poi["category"].isin(selected_categories)]

    st.pydeck_chart(
        build_map(
            properties=filtered_properties,
            poi=filtered_poi,
            center_lat=float(center["lat"]),
            center_lon=float(center["lon"]),
            zoom=int(settings["default_map_zoom"]),
        ),
        use_container_width=True,
    )

    metric_cols = st.columns(3)
    metric_cols[0].metric("Properties", len(filtered_properties))
    metric_cols[1].metric("POIs", len(filtered_poi))
    metric_cols[2].metric("Database", "ready" if Path(database_path).exists() else "not built")

    if filtered_properties.empty and filtered_poi.empty:
        st.info("Load POIs and property listings to populate the map.")


if __name__ == "__main__":
    main()
