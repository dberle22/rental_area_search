"""Property Explorer Streamlit app."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st

from nyc_property_finder.app.explorer import (
    CONTEXT_COLUMNS,
    CONTEXT_TABLE,
    NTA_FEATURE_TABLE,
    POI_TABLE,
    SHORTLIST_TABLE,
    SORT_OPTIONS,
    SUBWAY_TABLE,
    PropertyFilters,
    apply_property_filters,
    available_poi_categories,
    display_category_counts,
    join_shortlist_status,
    load_optional_table,
    load_shortlist,
    score_label,
    score_status_message,
    selected_property_id,
    sort_properties,
    status_label,
    summarize_visible_properties,
    table_exists,
    upsert_shortlist_row,
)
from nyc_property_finder.services.config import PROJECT_ROOT, load_config


st.set_page_config(page_title="Property Explorer", layout="wide")


@st.cache_data
def cached_load_table(database_path: str, table_name: str, expected_columns: tuple[str, ...] = ()) -> pd.DataFrame:
    """Cached wrapper around optional DuckDB table loading."""

    return load_optional_table(database_path, table_name, list(expected_columns))


@st.cache_data
def cached_load_shortlist(database_path: str, user_id: str) -> pd.DataFrame:
    """Cached shortlist table read."""

    return load_shortlist(database_path, user_id)


def _format_currency(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Price unavailable"
    return f"${float(value):,.0f}"


def _format_number(value: Any, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "Unavailable"
    return f"{float(value):g}{suffix}"


def _format_distance(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Subway distance unavailable"
    return f"{float(value):.2f} mi straight-line"


def _safe_unique(dataframe: pd.DataFrame, column: str) -> list[str]:
    if dataframe.empty or column not in dataframe.columns:
        return []
    return sorted(value for value in dataframe[column].dropna().astype(str).unique() if value)


def _numeric_min_max(dataframe: pd.DataFrame, column: str, fallback: tuple[float, float]) -> tuple[float, float]:
    if dataframe.empty or column not in dataframe.columns:
        return fallback
    values = pd.to_numeric(dataframe[column], errors="coerce").dropna()
    if values.empty:
        return fallback
    return float(values.min()), float(values.max())


def _prepare_layer_data(dataframe: pd.DataFrame, layer_type: str) -> pd.DataFrame:
    output = dataframe.copy()
    if output.empty:
        return output

    if layer_type == "property":
        output["marker_label"] = output["address"].fillna("Property")
        output["marker_detail"] = (
            output["price"].apply(_format_currency)
            + " | "
            + output["beds"].apply(lambda value: f"{_format_number(value)} bed")
            + " | "
            + output["nta_name"].fillna("Neighborhood unavailable")
        )
    elif layer_type == "poi":
        output["marker_label"] = output["name"].fillna("Personal POI")
        output["marker_detail"] = (
            output["category"].fillna("other").astype(str)
            + " | "
            + output["source_list_name"].fillna("Google Maps").astype(str)
        )
    else:
        output["marker_label"] = output["stop_name"].fillna("Subway stop")
        output["marker_detail"] = output["lines"].fillna("").astype(str)

    output["marker_type"] = layer_type.title()
    return output.dropna(subset=["lat", "lon"])


def point_layer(
    dataframe: pd.DataFrame,
    color: list[int],
    radius: int,
    layer_id: str,
) -> pdk.Layer | None:
    """Create a PyDeck point layer from lon/lat records."""

    if dataframe.empty or not {"lat", "lon"}.issubset(dataframe.columns):
        return None

    return pdk.Layer(
        "ScatterplotLayer",
        id=layer_id,
        data=dataframe,
        get_position="[lon, lat]",
        get_fill_color=color,
        get_radius=radius,
        pickable=True,
        auto_highlight=True,
    )


def build_map(
    properties: pd.DataFrame,
    poi: pd.DataFrame,
    subway: pd.DataFrame,
    selected_id: str | None,
    center_lat: float,
    center_lon: float,
    zoom: int,
) -> pdk.Deck:
    """Build the map with property, POI, and subway layers."""

    properties_with_flags = _prepare_layer_data(properties, "property")
    if selected_id and "property_id" in properties_with_flags.columns:
        selected_properties = properties_with_flags[
            properties_with_flags["property_id"].astype(str) == selected_id
        ]
        other_properties = properties_with_flags[
            properties_with_flags["property_id"].astype(str) != selected_id
        ]
    else:
        selected_properties = pd.DataFrame()
        other_properties = properties_with_flags

    candidate_layers = [
        point_layer(_prepare_layer_data(subway, "subway"), [30, 30, 30, 150], 38, "subway-stops"),
        point_layer(_prepare_layer_data(poi, "poi"), [42, 125, 225, 165], 46, "personal-pois"),
        point_layer(other_properties, [214, 73, 64, 205], 72, "properties"),
        point_layer(selected_properties, [250, 191, 47, 240], 115, "selected-property"),
    ]
    layers = [layer for layer in candidate_layers if layer is not None]

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom, pitch=0)
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="light",
        tooltip={"text": "{marker_type}: {marker_label}\n{marker_detail}"},
    )


def build_filters(context: pd.DataFrame, poi_categories: list[str]) -> tuple[PropertyFilters, str, bool, bool]:
    """Render sidebar controls and return selected app controls."""

    price_min, price_max = _numeric_min_max(context, "price", (0.0, 10000.0))
    if price_min == price_max:
        price_max = price_min + 1

    listing_types = _safe_unique(context, "listing_type")
    sources = _safe_unique(context, "source")
    ntas = _safe_unique(context, "nta_name")
    shortlist_statuses = _safe_unique(context, "shortlist_status")

    with st.sidebar:
        st.header("Filters")
        include_inactive = st.checkbox("Include inactive listings", value=False)

        selected_listing_types = st.multiselect(
            "Listing type",
            listing_types,
            default=listing_types,
        )
        selected_sources = st.multiselect("Source", sources, default=sources)
        selected_ntas = st.multiselect("Neighborhood", ntas, default=ntas)

        selected_price = st.slider(
            "Price range",
            min_value=int(price_min),
            max_value=int(price_max),
            value=(int(price_min), int(price_max)),
            step=250,
        )
        min_beds = st.number_input("Minimum beds", min_value=0.0, value=0.0, step=0.5)
        min_baths = st.number_input("Minimum baths", min_value=0.0, value=0.0, step=0.5)
        max_subway = st.slider(
            "Max subway distance",
            min_value=0.0,
            max_value=2.0,
            value=2.0,
            step=0.1,
            help="Straight-line MVP proximity proxy.",
        )

        st.subheader("Scores")
        min_property_fit = st.slider("Minimum total fit", 0, 100, 0, 5)
        min_mobility = st.slider("Minimum mobility", 0, 100, 0, 5)
        min_personal_fit = st.slider("Minimum personal fit", 0, 100, 0, 5)

        selected_poi_categories = st.multiselect(
            "Nearby personal POI category",
            poi_categories,
            default=[],
            help="Filters listings with at least one nearby saved place in the selected category.",
        )

        selected_shortlist_statuses: list[str] = []
        if shortlist_statuses:
            selected_shortlist_statuses = st.multiselect(
                "Shortlist status",
                shortlist_statuses,
                default=[],
            )

        st.subheader("Map layers")
        show_poi = st.checkbox("Show Google Maps POIs", value=True)
        show_subway = st.checkbox("Show subway stops", value=True)

        sort_label = st.selectbox("Sort listings", list(SORT_OPTIONS), index=0)

    filters = PropertyFilters(
        include_inactive=include_inactive,
        listing_types=tuple(selected_listing_types),
        sources=tuple(selected_sources),
        ntas=tuple(selected_ntas),
        price_min=float(selected_price[0]),
        price_max=float(selected_price[1]),
        min_beds=float(min_beds),
        min_baths=float(min_baths),
        max_subway_distance_miles=float(max_subway),
        min_property_fit_score=float(min_property_fit) if min_property_fit > 0 else None,
        min_mobility_score=float(min_mobility) if min_mobility > 0 else None,
        min_personal_fit_score=float(min_personal_fit) if min_personal_fit > 0 else None,
        poi_categories=tuple(selected_poi_categories),
        shortlist_statuses=tuple(selected_shortlist_statuses),
    )
    return filters, sort_label, show_poi, show_subway


def render_data_status(database_path: str, table_status: dict[str, bool]) -> None:
    """Render compact data readiness in the sidebar."""

    with st.sidebar:
        st.header("Data")
        st.caption(f"Database: `{database_path}`")
        if not Path(database_path).exists():
            st.error("Database file is missing. Build Sprint 2 and Sprint 3 tables first.")
            return
        for label, exists in table_status.items():
            st.write(f"{label}: {'ready' if exists else 'missing'}")


def render_metrics(visible_properties: pd.DataFrame, poi: pd.DataFrame, shortlist: pd.DataFrame) -> None:
    """Render top-level app metrics."""

    summary = summarize_visible_properties(visible_properties)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Visible listings", summary["count"])
    if summary["min_price"] is None or pd.isna(summary["min_price"]):
        metric_cols[1].metric("Price range", "Unavailable")
    else:
        metric_cols[1].metric(
            "Price range",
            f"{_format_currency(summary['min_price'])} to {_format_currency(summary['max_price'])}",
        )
    metric_cols[2].metric("Median total fit", score_label(summary["median_fit"]))
    active_shortlist = 0
    if not shortlist.empty and "status" in shortlist.columns:
        active_shortlist = int((shortlist["status"] == "active").sum())
    metric_cols[3].metric("Active shortlist", active_shortlist)
    st.caption(f"Context layers loaded: {len(poi)} Google Maps POIs.")


def render_listing_cards(properties: pd.DataFrame, selected_id: str | None) -> None:
    """Render selectable listing cards."""

    st.subheader("Listings")
    if properties.empty:
        st.info("No listings match the current filters.")
        return

    for row in properties.to_dict("records"):
        property_id = str(row.get("property_id", ""))
        selected = property_id == selected_id
        prefix = "Selected: " if selected else ""
        st.markdown(f"**{prefix}{_format_currency(row.get('price'))} | {row.get('address', 'Address unavailable')}**")
        st.caption(
            f"{_format_number(row.get('beds'))} bed | "
            f"{_format_number(row.get('baths'))} bath | "
            f"{str(row.get('listing_type') or 'type unavailable').title()} | "
            f"{row.get('nta_name') or 'Neighborhood unavailable'}"
        )
        st.write(
            f"{row.get('nearest_subway_stop') or 'Nearest subway unavailable'} "
            f"({_format_distance(row.get('nearest_subway_distance_miles'))})"
        )
        st.caption(
            f"Total {score_label(row.get('property_fit_score'))} "
            f"({status_label(row.get('property_fit_score_status'))}) | "
            f"Mobility {score_label(row.get('mobility_score'))} | "
            f"Personal {score_label(row.get('personal_fit_score'))}"
        )
        if row.get("shortlist_status"):
            st.caption(f"Shortlist: {status_label(row.get('shortlist_status'))}")
        if st.button("Details", key=f"select_{property_id}", use_container_width=True):
            st.session_state["selected_property_id"] = property_id
            st.rerun()
        st.divider()


def _selected_nta_features(selected: pd.Series, nta_features: pd.DataFrame) -> pd.Series | None:
    if nta_features.empty or "nta_id" not in nta_features.columns or pd.isna(selected.get("nta_id")):
        return None
    matches = nta_features[nta_features["nta_id"].astype(str) == str(selected.get("nta_id"))]
    if matches.empty:
        return None
    return matches.iloc[0]


def render_score_section(selected: pd.Series) -> None:
    """Render score breakdown and missing-data copy."""

    st.subheader("Score Breakdown")
    score_cols = st.columns(4)
    score_cols[0].metric("Total fit", score_label(selected.get("property_fit_score")))
    score_cols[1].metric("Mobility", score_label(selected.get("mobility_score")))
    score_cols[2].metric("Personal fit", score_label(selected.get("personal_fit_score")))
    score_cols[3].metric("Neighborhood", score_label(selected.get("neighborhood_score")))

    st.info(score_status_message("property_fit", selected.get("property_fit_score_status")))
    st.warning(score_status_message("neighborhood", selected.get("neighborhood_score_status")))
    if selected.get("personal_fit_score_status") != "scored":
        st.info(score_status_message("personal_fit", selected.get("personal_fit_score_status")))
    else:
        st.caption(score_status_message("personal_fit", selected.get("personal_fit_score_status")))


def render_shortlist_controls(database_path: str, user_id: str, selected: pd.Series, shortlist_available: bool) -> None:
    """Render save/archive/reject and notes controls for the selected property."""

    st.subheader("Shortlist")
    if not shortlist_available:
        st.info("Shortlist table is not available yet. Run database initialization before saving listings.")
        return

    property_id = str(selected.get("property_id"))
    current_status = selected.get("shortlist_status")
    current_notes = "" if pd.isna(selected.get("shortlist_notes")) else str(selected.get("shortlist_notes"))
    notes = st.text_area("Notes", value=current_notes, key=f"notes_{property_id}")
    control_cols = st.columns(3)

    if control_cols[0].button("Save", key=f"save_{property_id}", use_container_width=True):
        upsert_shortlist_row(database_path, user_id, property_id, status="active", notes=notes)
        cached_load_shortlist.clear()
        st.rerun()
    if control_cols[1].button("Archive", key=f"archive_{property_id}", use_container_width=True):
        upsert_shortlist_row(database_path, user_id, property_id, status="archived", notes=notes)
        cached_load_shortlist.clear()
        st.rerun()
    if control_cols[2].button("Reject", key=f"reject_{property_id}", use_container_width=True):
        upsert_shortlist_row(database_path, user_id, property_id, status="rejected", notes=notes)
        cached_load_shortlist.clear()
        st.rerun()

    if current_status and not pd.isna(current_status):
        st.caption(f"Current status: {status_label(current_status)}")
    else:
        st.caption("Not yet shortlisted.")


def render_detail(
    selected: pd.Series | None,
    nta_features: pd.DataFrame,
    database_path: str,
    user_id: str,
    shortlist_available: bool,
) -> None:
    """Render selected property detail."""

    st.subheader("Property Detail")
    if selected is None:
        st.info("Select a listing to see details.")
        return

    st.markdown(f"### {_format_currency(selected.get('price'))}")
    st.markdown(f"**{selected.get('address') or 'Address unavailable'}**")
    st.caption(
        f"{_format_number(selected.get('beds'))} bed | "
        f"{_format_number(selected.get('baths'))} bath | "
        f"{str(selected.get('listing_type') or 'type unavailable').title()} | "
        f"{selected.get('source') or 'source unavailable'}"
    )
    if selected.get("url") and not pd.isna(selected.get("url")):
        st.link_button("Open source listing", str(selected.get("url")))

    st.subheader("Context")
    st.write(f"Neighborhood: {selected.get('nta_name') or 'Unavailable'}")
    st.caption(f"NTA: {selected.get('nta_id') or 'Unavailable'} | Tract: {selected.get('tract_id') or 'Unavailable'}")
    st.write(
        f"Nearest subway: {selected.get('nearest_subway_stop') or 'Unavailable'} "
        f"({_format_distance(selected.get('nearest_subway_distance_miles'))})"
    )
    st.caption(f"Subway line count: {_format_number(selected.get('subway_lines_count'))}")
    st.write(f"Nearby personal POIs: {_format_number(selected.get('poi_count_nearby'))}")
    st.caption(display_category_counts(selected.get("poi_category_counts")))

    render_score_section(selected)

    st.subheader("Neighborhood Metrics")
    nta_row = _selected_nta_features(selected, nta_features)
    metric_names = {
        "median_income": "Median income",
        "median_rent": "Median rent",
        "median_home_value": "Median home value",
        "pct_bachelors_plus": "Bachelor's plus",
        "median_age": "Median age",
    }
    if nta_row is None or all(pd.isna(nta_row.get(column)) for column in metric_names):
        st.info("Neighborhood feature metrics are unavailable in the current Sprint 3 data.")
    else:
        metric_cols = st.columns(len(metric_names))
        for metric_col, (column, label) in zip(metric_cols, metric_names.items(), strict=True):
            value = nta_row.get(column)
            if column in {"median_income", "median_rent", "median_home_value"}:
                metric_col.metric(label, _format_currency(value))
            elif column == "pct_bachelors_plus":
                metric_col.metric(label, _format_number(value, "%"))
            else:
                metric_col.metric(label, _format_number(value))

    render_shortlist_controls(database_path, user_id, selected, shortlist_available)


def main() -> None:
    """Render the Streamlit app."""

    config = load_config()
    settings = config["settings"]
    database_path = str(PROJECT_ROOT / settings["database_path"])
    user_id = settings.get("local_user", {}).get("default_user_id", "local_default")
    center = settings["default_map_center"]

    table_status = {
        "Context": table_exists(database_path, CONTEXT_TABLE),
        "POIs": table_exists(database_path, POI_TABLE),
        "Subway": table_exists(database_path, SUBWAY_TABLE),
        "NTA features": table_exists(database_path, NTA_FEATURE_TABLE),
        "Shortlist": table_exists(database_path, SHORTLIST_TABLE),
    }

    context = cached_load_table(database_path, CONTEXT_TABLE, tuple(CONTEXT_COLUMNS))
    poi = cached_load_table(
        database_path,
        POI_TABLE,
        ("poi_id", "name", "category", "source_list_name", "lat", "lon"),
    )
    subway = cached_load_table(
        database_path,
        SUBWAY_TABLE,
        ("subway_stop_id", "stop_name", "lines", "lat", "lon"),
    )
    nta_features = cached_load_table(
        database_path,
        NTA_FEATURE_TABLE,
        (
            "nta_id",
            "nta_name",
            "median_income",
            "median_rent",
            "median_home_value",
            "pct_bachelors_plus",
            "median_age",
        ),
    )
    shortlist = cached_load_shortlist(database_path, user_id) if table_status["Shortlist"] else pd.DataFrame()
    context = join_shortlist_status(context, shortlist)

    st.title("Property Explorer")
    st.caption("Local map/list/detail review for NYC property candidates.")

    render_data_status(database_path, table_status)

    if not table_status["Context"] or context.empty:
        st.info(
            "Build `property_explorer_gold.fct_property_context` before using the explorer. "
            "Sprint 4 reads this table as the primary app contract."
        )
        return

    poi_categories = available_poi_categories(context)
    filters, sort_label, show_poi, show_subway = build_filters(context, poi_categories)
    filtered = sort_properties(apply_property_filters(context, filters), sort_label)

    current_selection = st.session_state.get("selected_property_id")
    valid_selection = selected_property_id(current_selection, filtered)
    st.session_state["selected_property_id"] = valid_selection

    selected_row = None
    if valid_selection and "property_id" in filtered.columns:
        selected_matches = filtered[filtered["property_id"].astype(str) == valid_selection]
        if not selected_matches.empty:
            selected_row = selected_matches.iloc[0]

    render_metrics(filtered, poi, shortlist)

    map_poi = poi if show_poi else pd.DataFrame()
    map_subway = subway if show_subway else pd.DataFrame()
    map_col, detail_col = st.columns([1.35, 1])
    with map_col:
        st.pydeck_chart(
            build_map(
                properties=filtered,
                poi=map_poi,
                subway=map_subway,
                selected_id=valid_selection,
                center_lat=float(center["lat"]),
                center_lon=float(center["lon"]),
                zoom=int(settings["default_map_zoom"]),
            ),
            use_container_width=True,
        )
        st.caption("Distances and nearby POI counts use straight-line MVP proximity proxies.")
        render_listing_cards(filtered, valid_selection)

    with detail_col:
        render_detail(
            selected_row,
            nta_features,
            database_path,
            user_id,
            shortlist_available=table_status["Shortlist"],
        )


if __name__ == "__main__":
    main()
