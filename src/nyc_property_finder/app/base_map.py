"""Reusable map helpers for the Neighborhood Explorer Streamlit app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pydeck as pdk

from nyc_property_finder.app.explorer import load_optional_table, table_exists


GOLD_SCHEMA = "property_explorer_gold"
TRACT_FEATURE_TABLE = f"{GOLD_SCHEMA}.fct_tract_features"
NTA_FEATURE_TABLE = f"{GOLD_SCHEMA}.fct_nta_features"
TRACT_TO_NTA_TABLE = f"{GOLD_SCHEMA}.dim_tract_to_nta"

TARGET_COUNTY_GEOIDS = ("36047", "36061")
TARGET_BOROUGHS = ("Brooklyn", "Manhattan")

DEMOGRAPHIC_METRICS: dict[str, dict[str, str]] = {
    "median_income": {"label": "Median household income", "format": "currency"},
    "median_rent": {"label": "Median gross rent", "format": "currency"},
    "median_home_value": {"label": "Median home value", "format": "currency"},
    "pct_bachelors_plus": {"label": "Bachelor's plus", "format": "percent"},
    "median_age": {"label": "Median age", "format": "number"},
}

BASE_COLUMNS = [
    "tract_id",
    "nta_id",
    "nta_name",
    "borough",
    *DEMOGRAPHIC_METRICS.keys(),
]

EMPTY_MAP_STATS = {
    "tract_count": 0,
    "neighborhood_count": 0,
    "metric_non_null_count": 0,
    "metric_coverage": 0.0,
}


@dataclass(frozen=True)
class BaseMapData:
    """Prepared tract and neighborhood map layers."""

    tracts: gpd.GeoDataFrame
    neighborhoods: gpd.GeoDataFrame
    metric: str
    stats: dict[str, Any]


def metric_label(metric: str) -> str:
    """Return a display label for a demographic metric."""

    return DEMOGRAPHIC_METRICS.get(metric, {}).get("label", metric.replace("_", " ").title())


def metric_options() -> dict[str, str]:
    """Return Streamlit-friendly metric labels keyed by metric column."""

    return {metric: metric_label(metric) for metric in DEMOGRAPHIC_METRICS}


def format_metric_value(value: Any, metric: str) -> str:
    """Format a demographic value for map tooltips and detail tables."""

    if value is None or pd.isna(value):
        return "Unavailable"

    metric_format = DEMOGRAPHIC_METRICS.get(metric, {}).get("format", "number")
    numeric = float(value)
    if metric_format == "currency":
        return f"${numeric:,.0f}"
    if metric_format == "percent":
        percent_value = numeric * 100 if 0 <= numeric <= 1 else numeric
        return f"{percent_value:.1f}%"
    return f"{numeric:g}"


def normalize_metric_series(values: pd.Series) -> pd.Series:
    """Normalize a numeric series to 0-1 for color ramps."""

    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.Series(0.0, index=values.index)

    min_value = float(valid.min())
    max_value = float(valid.max())
    if min_value == max_value:
        return pd.Series(0.5, index=values.index).where(numeric.notna(), 0.0)

    normalized = (numeric - min_value) / (max_value - min_value)
    return normalized.clip(0, 1).fillna(0.0)


def color_for_value(normalized_value: float, has_value: bool) -> list[int]:
    """Return a muted blue-green ramp color for a normalized metric value."""

    if not has_value:
        return [198, 202, 208, 58]

    t = max(0.0, min(1.0, float(normalized_value)))
    low = (241, 245, 232)
    mid = (91, 169, 157)
    high = (34, 82, 111)
    if t < 0.5:
        local_t = t / 0.5
        start, end = low, mid
    else:
        local_t = (t - 0.5) / 0.5
        start, end = mid, high

    rgb = [round(start[index] + (end[index] - start[index]) * local_t) for index in range(3)]
    return [*rgb, 178]


def add_metric_display_columns(dataframe: gpd.GeoDataFrame, metric: str) -> gpd.GeoDataFrame:
    """Add tooltip and color fields for a selected metric."""

    output = dataframe.copy()
    if metric not in output.columns:
        output[metric] = pd.NA

    numeric = pd.to_numeric(output[metric], errors="coerce")
    normalized = normalize_metric_series(numeric)
    output["selected_metric"] = metric
    output["selected_metric_label"] = metric_label(metric)
    output["selected_metric_value"] = numeric
    output["selected_metric_display"] = [format_metric_value(value, metric) for value in numeric]
    output["metric_available"] = numeric.notna()
    output["fill_color"] = [
        color_for_value(value, has_value)
        for value, has_value in zip(normalized, output["metric_available"], strict=True)
    ]
    return output


def load_mapping(database_path: str | Path) -> pd.DataFrame:
    """Load the tract-to-NTA mapping from the gold schema."""

    return load_optional_table(
        database_path,
        TRACT_TO_NTA_TABLE,
        ["tract_id", "nta_id", "nta_name", "borough"],
    )


def load_feature_table(
    database_path: str | Path,
    full_table_name: str,
    id_columns: list[str],
) -> pd.DataFrame:
    """Load a demographic feature table with expected metric columns."""

    return load_optional_table(
        database_path,
        full_table_name,
        [*id_columns, *DEMOGRAPHIC_METRICS.keys()],
    )


def load_tract_geometries(
    tract_path: str | Path,
    tract_id_col: str = "GEOID",
    target_county_geoids: tuple[str, ...] = TARGET_COUNTY_GEOIDS,
) -> gpd.GeoDataFrame:
    """Load target Brooklyn and Manhattan tract geometries."""

    tracts = gpd.read_file(tract_path)
    if tract_id_col not in tracts.columns:
        raise ValueError(f"Missing tract id column in tract geometry file: {tract_id_col}")

    tracts = tracts.rename(columns={tract_id_col: "tract_id"}).to_crs("EPSG:4326")
    tracts["tract_id"] = (
        tracts["tract_id"]
        .fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(11)
    )
    target_mask = tracts["tract_id"].str.startswith(target_county_geoids)
    columns = [
        column
        for column in ["tract_id", "BoroName", "NTA2020", "NTAName", "geometry"]
        if column in tracts.columns
    ]
    return tracts.loc[target_mask, columns].copy()


def attach_tract_attributes(
    tracts: gpd.GeoDataFrame,
    mapping: pd.DataFrame,
    tract_features: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Attach NTA labels and tract demographic metrics to tract geometries."""

    output = tracts.copy()
    if "BoroName" in output.columns:
        output = output.rename(columns={"BoroName": "geometry_borough"})

    mapping_columns = [
        column
        for column in ["tract_id", "nta_id", "nta_name", "borough"]
        if column in mapping.columns
    ]
    if mapping_columns:
        output = output.merge(
            mapping[mapping_columns].drop_duplicates("tract_id"),
            on="tract_id",
            how="left",
        )

    if "nta_id" not in output.columns and "NTA2020" in output.columns:
        output["nta_id"] = output["NTA2020"]
    if "nta_name" not in output.columns and "NTAName" in output.columns:
        output["nta_name"] = output["NTAName"]
    if "borough" not in output.columns:
        output["borough"] = output.get("geometry_borough", pd.NA)

    feature_columns = [
        column
        for column in ["tract_id", *DEMOGRAPHIC_METRICS.keys()]
        if column in tract_features.columns
    ]
    if feature_columns:
        output = output.merge(
            tract_features[feature_columns].drop_duplicates("tract_id"),
            on="tract_id",
            how="left",
        )

    for column in BASE_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    return output[BASE_COLUMNS + ["geometry"]].copy()


def build_neighborhood_geometries(
    tract_map: gpd.GeoDataFrame,
    nta_features: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Dissolve tracts into neighborhood boundaries and attach NTA metrics."""

    if tract_map.empty:
        return gpd.GeoDataFrame(
            columns=BASE_COLUMNS + ["geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    dissolved = (
        tract_map.dissolve(
            by=["nta_id", "nta_name", "borough"],
            as_index=False,
            dropna=False,
        )[["nta_id", "nta_name", "borough", "geometry"]]
        .copy()
    )

    feature_columns = [
        column
        for column in ["nta_id", "nta_name", *DEMOGRAPHIC_METRICS.keys()]
        if column in nta_features.columns
    ]
    if feature_columns:
        dissolved = dissolved.merge(
            nta_features[feature_columns].drop_duplicates("nta_id"),
            on=["nta_id", "nta_name"] if "nta_name" in feature_columns else ["nta_id"],
            how="left",
        )

    for metric in DEMOGRAPHIC_METRICS:
        if metric not in dissolved.columns:
            dissolved[metric] = pd.NA
    if "tract_id" not in dissolved.columns:
        dissolved["tract_id"] = pd.NA
    return dissolved[BASE_COLUMNS + ["geometry"]].copy()


def prepare_base_map_data(
    database_path: str | Path,
    tract_path: str | Path,
    tract_id_col: str = "GEOID",
    metric: str = "median_income",
) -> BaseMapData:
    """Load and prepare Neighborhood Explorer tract and neighborhood layers."""

    if metric not in DEMOGRAPHIC_METRICS:
        raise ValueError(f"Unsupported demographic metric: {metric}")

    mapping = load_mapping(database_path)
    tract_features = load_feature_table(database_path, TRACT_FEATURE_TABLE, ["tract_id"])
    nta_features = load_feature_table(database_path, NTA_FEATURE_TABLE, ["nta_id", "nta_name"])

    tracts = load_tract_geometries(tract_path, tract_id_col=tract_id_col)
    tract_map = attach_tract_attributes(tracts, mapping, tract_features)
    neighborhoods = build_neighborhood_geometries(tract_map, nta_features)

    tract_map = add_metric_display_columns(tract_map, metric)
    neighborhoods = add_metric_display_columns(neighborhoods, metric)

    metric_values = (
        pd.to_numeric(tract_map[metric], errors="coerce")
        if metric in tract_map
        else pd.Series(dtype="float64")
    )
    stats = {
        "tract_count": int(len(tract_map)),
        "neighborhood_count": (
            int(neighborhoods["nta_id"].nunique(dropna=True))
            if "nta_id" in neighborhoods
            else 0
        ),
        "metric_non_null_count": int(metric_values.notna().sum()),
        "metric_coverage": float(metric_values.notna().mean()) if len(metric_values) else 0.0,
        "metric_label": metric_label(metric),
        "database_ready": Path(database_path).exists(),
        "mapping_ready": table_exists(database_path, TRACT_TO_NTA_TABLE),
        "tract_features_ready": table_exists(database_path, TRACT_FEATURE_TABLE),
        "nta_features_ready": table_exists(database_path, NTA_FEATURE_TABLE),
    }

    return BaseMapData(tracts=tract_map, neighborhoods=neighborhoods, metric=metric, stats=stats)


def _geojson_records(dataframe: gpd.GeoDataFrame) -> dict[str, Any]:
    display_columns = [
        "tract_id",
        "nta_id",
        "nta_name",
        "borough",
        "selected_metric_label",
        "selected_metric_display",
        "metric_available",
        "fill_color",
        "geometry",
    ]
    available_columns = [column for column in display_columns if column in dataframe.columns]
    clean = dataframe[available_columns].copy()
    if not clean.empty:
        clean["geometry"] = clean.geometry.simplify(0.00008, preserve_topology=True)
    return clean.__geo_interface__


def build_base_map_deck(
    map_data: BaseMapData,
    layer_mode: str = "Tracts",
    center_lat: float = 40.7128,
    center_lon: float = -74.0060,
    zoom: int = 10,
) -> pdk.Deck:
    """Build a PyDeck map for the selected geography layer."""

    show_neighborhoods = layer_mode == "Neighborhoods"
    primary = map_data.neighborhoods if show_neighborhoods else map_data.tracts
    outline = map_data.tracts if show_neighborhoods else map_data.neighborhoods

    layers = [
        pdk.Layer(
            "GeoJsonLayer",
            id="base-context-outline",
            data=_geojson_records(outline),
            stroked=True,
            filled=False,
            get_line_color=[32, 36, 40, 75],
            get_line_width=22 if show_neighborhoods else 34,
            line_width_min_pixels=1,
            pickable=False,
        ),
        pdk.Layer(
            "GeoJsonLayer",
            id="base-context-fill",
            data=_geojson_records(primary),
            stroked=True,
            filled=True,
            get_fill_color="properties.fill_color",
            get_line_color=[22, 28, 32, 145],
            get_line_width=54 if show_neighborhoods else 26,
            line_width_min_pixels=1,
            pickable=True,
            auto_highlight=True,
        ),
    ]
    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom, pitch=0)
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="light",
        tooltip={
            "html": (
                "<b>{nta_name}</b><br/>"
                "Tract: {tract_id}<br/>"
                "{selected_metric_label}: {selected_metric_display}"
            )
        },
    )
