"""Reusable map helpers for the Neighborhood Explorer Streamlit app."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pydeck as pdk
from shapely.geometry import MultiPolygon, Polygon

from nyc_property_finder.app.explorer import load_optional_table, table_exists
from nyc_property_finder.google_places_poi.build_dim import build_dim_user_poi_v2
from nyc_property_finder.google_places_poi.cache import read_details_cache
from nyc_property_finder.google_places_poi.config import (
    DEFAULT_DETAILS_CACHE_PATH,
    DEFAULT_RESOLUTION_CACHE_PATH,
)


GOLD_SCHEMA = "property_explorer_gold"
TRACT_FEATURE_TABLE = f"{GOLD_SCHEMA}.fct_tract_features"
NTA_FEATURE_TABLE = f"{GOLD_SCHEMA}.fct_nta_features"
TRACT_TO_NTA_TABLE = f"{GOLD_SCHEMA}.dim_tract_to_nta"
POI_TABLE = f"{GOLD_SCHEMA}.dim_user_poi"
POI_V2_TABLE = f"{GOLD_SCHEMA}.dim_user_poi_v2"

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

POI_COLUMNS = [
    "poi_id",
    "source_list_names",
    "categories",
    "primary_category",
    "name",
    "input_title",
    "address",
    "lat",
    "lon",
]

POI_COLOR_PALETTE = [
    [205, 83, 64, 230],
    [45, 129, 150, 230],
    [233, 169, 55, 230],
    [92, 111, 191, 230],
    [71, 151, 102, 230],
    [174, 88, 157, 230],
    [39, 98, 113, 230],
    [190, 104, 54, 230],
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


@dataclass(frozen=True)
class PoiMapData:
    """Prepared point-of-interest layer records."""

    points: pd.DataFrame
    source: str
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


def parse_json_text_array(value: Any) -> list[str]:
    """Parse a JSON text array or scalar value into clean display strings."""

    if isinstance(value, list | tuple | set):
        raw_values = list(value)
    else:
        if value is None or pd.isna(value):
            return []
        text = str(value).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = text
        raw_values = parsed if isinstance(parsed, list) else [parsed]

    cleaned = []
    for item in raw_values:
        item_text = str(item).strip()
        if item_text and item_text not in cleaned:
            cleaned.append(item_text)
    return cleaned


def format_poi_list_name(value: str) -> str:
    """Return a readable POI source-list label."""

    text = str(value).strip()
    return text if text else "Unlisted POIs"


def format_poi_category(value: Any) -> str:
    """Return a readable POI category label."""

    text = str(value).strip()
    return text.replace("_", " ").title() if text else "Other"


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


def add_demographic_summary_columns(dataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add formatted demographic fields for summary tooltips."""

    output = dataframe.copy()
    for metric in DEMOGRAPHIC_METRICS:
        if metric not in output.columns:
            output[metric] = pd.NA
        output[f"{metric}_display"] = [
            format_metric_value(value, metric)
            for value in pd.to_numeric(output[metric], errors="coerce")
        ]
    return output


def add_tooltip_columns(dataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add pre-rendered tooltip text for flat PyDeck polygon records."""

    output = dataframe.copy()
    output["selected_metric_tooltip"] = (
        "<b>"
        + output["nta_name"].fillna("Unavailable").astype(str)
        + "</b><br/>Tract: "
        + output["tract_id"].fillna("Unavailable").astype(str)
        + "<br/>"
        + output["selected_metric_label"].fillna("Metric").astype(str)
        + ": "
        + output["selected_metric_display"].fillna("Unavailable").astype(str)
    )
    output["nta_summary_tooltip"] = (
        "<b>"
        + output["nta_name"].fillna("Unavailable").astype(str)
        + "</b><br/>"
        + output["borough"].fillna("Unavailable").astype(str)
        + "<br/>Median household income: "
        + output["median_income_display"].fillna("Unavailable").astype(str)
        + "<br/>Median gross rent: "
        + output["median_rent_display"].fillna("Unavailable").astype(str)
        + "<br/>Median home value: "
        + output["median_home_value_display"].fillna("Unavailable").astype(str)
        + "<br/>Bachelor's plus: "
        + output["pct_bachelors_plus_display"].fillna("Unavailable").astype(str)
        + "<br/>Median age: "
        + output["median_age_display"].fillna("Unavailable").astype(str)
    )
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


def load_poi_map_data(
    database_path: str | Path,
    resolution_cache_path: str | Path = DEFAULT_RESOLUTION_CACHE_PATH,
    details_cache_path: str | Path = DEFAULT_DETAILS_CACHE_PATH,
) -> PoiMapData:
    """Load app-ready POIs, preferring DuckDB v2 and falling back to caches."""

    source = "unavailable"
    poi = pd.DataFrame(columns=POI_COLUMNS)

    if table_exists(database_path, POI_V2_TABLE):
        poi = load_optional_table(database_path, POI_V2_TABLE, POI_COLUMNS)
        source = "duckdb_v2"

    if poi.empty and table_exists(database_path, POI_TABLE):
        legacy = load_optional_table(
            database_path,
            POI_TABLE,
            ["poi_id", "name", "category", "source_list_name", "lat", "lon"],
        )
        if not legacy.empty:
            poi = legacy.rename(
                columns={
                    "category": "primary_category",
                    "source_list_name": "source_list_names",
                }
            )
            poi["categories"] = poi["primary_category"]
            poi["input_title"] = poi["name"]
            poi["address"] = ""
            source = "duckdb_legacy"

    if poi.empty:
        poi = build_dim_user_poi_v2(
            resolution_cache_path=resolution_cache_path,
            details_cache_path=details_cache_path,
        )
        source = "cache_v2" if not poi.empty else source

    if poi.empty:
        poi = _poi_dataframe_from_details_cache(details_cache_path)
        source = "details_cache" if not poi.empty else source

    points = prepare_poi_points(poi)
    return PoiMapData(
        points=points,
        source=source,
        stats={
            "poi_count": int(len(points)),
            "source_list_count": len(available_poi_source_lists(points)),
        },
    )


def _poi_dataframe_from_details_cache(details_cache_path: str | Path) -> pd.DataFrame:
    """Build minimal POI records when only Place Details cache rows are available."""

    rows = []
    for google_place_id, row in read_details_cache(details_cache_path).items():
        payload = row.get("payload", {}) if isinstance(row, dict) else {}
        if not isinstance(payload, dict):
            continue
        display_name = payload.get("displayName", {})
        location = payload.get("location", {})
        rows.append(
            {
                "poi_id": f"google_place_{google_place_id}",
                "source_list_names": json.dumps(["Google Places cache"]),
                "categories": json.dumps(["google_places_cache"]),
                "primary_category": "google_places_cache",
                "name": display_name.get("text", google_place_id)
                if isinstance(display_name, dict)
                else google_place_id,
                "input_title": "",
                "address": payload.get("formattedAddress", ""),
                "lat": location.get("latitude") if isinstance(location, dict) else None,
                "lon": location.get("longitude") if isinstance(location, dict) else None,
            }
        )
    return pd.DataFrame(rows, columns=POI_COLUMNS)


def prepare_poi_points(poi: pd.DataFrame) -> pd.DataFrame:
    """Normalize POI records for PyDeck filtering and hover tooltips."""

    output = poi.copy()
    for column in POI_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA

    output["lat"] = pd.to_numeric(output["lat"], errors="coerce")
    output["lon"] = pd.to_numeric(output["lon"], errors="coerce")
    output = output.dropna(subset=["lat", "lon"]).copy()
    if output.empty:
        return output

    output["source_list_values"] = output["source_list_names"].apply(parse_json_text_array)
    output["source_list_values"] = output["source_list_values"].apply(
        lambda values: values or ["Unlisted POIs"]
    )
    output["primary_source_list"] = output["source_list_values"].apply(
        lambda values: format_poi_list_name(values[0])
    )
    output["source_list_display"] = output["source_list_values"].apply(
        lambda values: ", ".join(format_poi_list_name(value) for value in values)
    )
    output["category_values"] = output["categories"].apply(parse_json_text_array)
    output["category_display"] = [
        format_poi_category(category or primary)
        for category, primary in zip(
            output["category_values"].apply(lambda values: values[0] if values else ""),
            output["primary_category"].fillna(""),
            strict=True,
        )
    ]

    source_lists = available_poi_source_lists(output)
    color_lookup = {
        source_list: POI_COLOR_PALETTE[index % len(POI_COLOR_PALETTE)]
        for index, source_list in enumerate(source_lists)
    }
    output["poi_color"] = output["primary_source_list"].map(color_lookup).apply(
        lambda color: color if isinstance(color, list) else [205, 83, 64, 230]
    )
    output["tooltip_html"] = (
        "<b>"
        + output["name"].fillna("Unnamed POI").astype(str)
        + "</b><br/>List: "
        + output["source_list_display"].fillna("Unlisted POIs").astype(str)
        + "<br/>Type: "
        + output["category_display"].fillna("Other").astype(str)
        + "<br/>"
        + output["address"].fillna("").astype(str)
    )
    return output


def available_poi_source_lists(poi: pd.DataFrame) -> list[str]:
    """Return sorted source-list labels available in a POI dataframe."""

    if poi.empty or "source_list_values" not in poi.columns:
        return []

    values = set()
    for source_lists in poi["source_list_values"]:
        values.update(format_poi_list_name(value) for value in source_lists)
    return sorted(values)


def filter_poi_points_by_source_lists(
    poi: pd.DataFrame,
    selected_source_lists: tuple[str, ...],
) -> pd.DataFrame:
    """Filter POIs to any selected Google Maps source list."""

    if poi.empty or not selected_source_lists:
        return poi.iloc[0:0].copy()

    selected = set(selected_source_lists)
    mask = poi["source_list_values"].apply(
        lambda values: bool(selected.intersection(format_poi_list_name(value) for value in values))
    )
    return poi.loc[mask].copy()


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

    tract_map = add_tooltip_columns(
        add_demographic_summary_columns(add_metric_display_columns(tract_map, metric))
    )
    neighborhoods = add_tooltip_columns(
        add_demographic_summary_columns(add_metric_display_columns(neighborhoods, metric))
    )

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


def _polygon_coordinates(geometry: Polygon) -> list[list[list[float]]]:
    exterior = [[float(x), float(y)] for x, y in geometry.exterior.coords]
    interiors = [
        [[float(x), float(y)] for x, y in interior.coords]
        for interior in geometry.interiors
    ]
    return [exterior, *interiors]


def _polygon_records(dataframe: gpd.GeoDataFrame, tooltip_column: str) -> list[dict[str, Any]]:
    display_columns = [
        "tract_id",
        "nta_id",
        "nta_name",
        "borough",
        "selected_metric_label",
        "selected_metric_display",
        "metric_available",
        "fill_color",
        *[f"{metric}_display" for metric in DEMOGRAPHIC_METRICS],
        tooltip_column,
    ]
    available_columns = [column for column in display_columns if column in dataframe.columns]
    records = []
    for row in dataframe[[*available_columns, "geometry"]].itertuples(index=False):
        record = {
            column: getattr(row, column)
            for column in available_columns
            if column != "geometry"
        }
        record["tooltip_html"] = record.get(tooltip_column, "")
        geometry = row.geometry
        if geometry is None or geometry.is_empty:
            continue
        simplified = geometry.simplify(0.00008, preserve_topology=True)
        polygons = simplified.geoms if isinstance(simplified, MultiPolygon) else [simplified]
        for polygon in polygons:
            if not isinstance(polygon, Polygon) or polygon.is_empty:
                continue
            records.append({**record, "polygon": _polygon_coordinates(polygon)})
    return records


def build_base_map_deck(
    map_data: BaseMapData,
    layer_mode: str = "Tracts",
    show_demographics: bool = True,
    poi_points: pd.DataFrame | None = None,
    show_pois: bool = False,
    center_lat: float = 40.7128,
    center_lon: float = -74.0060,
    zoom: int = 10,
) -> pdk.Deck:
    """Build a PyDeck map for the selected geography layer."""

    show_neighborhoods = layer_mode == "Neighborhoods"
    demographic_layer = map_data.neighborhoods if show_neighborhoods else map_data.tracts

    layers = []
    if show_demographics:
        layers.append(
            pdk.Layer(
                "PolygonLayer",
                id="demographic-fill",
                data=_polygon_records(demographic_layer, "selected_metric_tooltip"),
                get_polygon="polygon",
                stroked=True,
                filled=True,
                get_fill_color="fill_color",
                get_line_color=[22, 28, 32, 145],
                get_line_width=54 if show_neighborhoods else 26,
                line_width_min_pixels=1,
                pickable=True,
                auto_highlight=True,
            )
        )

    layers.append(
        pdk.Layer(
            "PolygonLayer",
            id="nta-boundaries",
            data=_polygon_records(map_data.neighborhoods, "nta_summary_tooltip"),
            get_polygon="polygon",
            stroked=True,
            filled=not show_demographics,
            get_line_color=[0, 0, 0, 210],
            get_line_width=46,
            line_width_min_pixels=1,
            get_fill_color=[0, 0, 0, 0],
            pickable=not show_demographics,
            auto_highlight=not show_demographics,
            highlight_color=[0, 0, 0, 28],
        )
    )

    if show_pois and poi_points is not None and not poi_points.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="poi-points",
                data=poi_points.to_dict("records"),
                get_position="[lon, lat]",
                get_fill_color="poi_color",
                get_line_color=[255, 255, 255, 230],
                get_radius=48,
                radius_min_pixels=5,
                radius_max_pixels=13,
                stroked=True,
                line_width_min_pixels=1,
                pickable=True,
                auto_highlight=True,
                highlight_color=[255, 255, 255, 90],
            )
        )

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom, pitch=0)
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="light",
        tooltip={"html": "{tooltip_html}"},
    )
