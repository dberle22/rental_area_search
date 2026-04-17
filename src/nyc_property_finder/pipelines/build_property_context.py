"""Build property context and scoring table."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from nyc_property_finder.services.duckdb_service import DuckDBService
from nyc_property_finder.transforms.scoring import (
    mobility_score,
    neighborhood_score,
    personal_fit_score,
    property_fit_score,
)
from nyc_property_finder.utils.geo import (
    count_points_within_radius,
    nearest_neighbor,
    points_from_lon_lat,
    spatial_join_points_to_polygons,
)


PROPERTY_CONTEXT_COLUMNS = [
    "property_id",
    "source",
    "source_listing_id",
    "address",
    "lat",
    "lon",
    "price",
    "beds",
    "baths",
    "listing_type",
    "url",
    "ingest_timestamp",
    "tract_id",
    "nta_id",
    "nearest_subway_stop",
    "nearest_subway_distance_miles",
    "subway_lines_count",
    "poi_count_10min",
    "poi_category_counts",
    "neighborhood_score",
    "mobility_score",
    "personal_fit_score",
    "property_fit_score",
]


def attach_geography(
    properties: pd.DataFrame,
    tracts,
    tract_id_col: str = "tract_id",
    nta_id_col: str = "nta_id",
) -> pd.DataFrame:
    """Join property points to tract and NTA attributes."""

    if properties.empty:
        output = properties.copy()
        output[tract_id_col] = pd.Series(dtype="object")
        output[nta_id_col] = pd.Series(dtype="object")
        return output

    property_points = points_from_lon_lat(properties)
    joined = spatial_join_points_to_polygons(
        points=property_points,
        polygons=tracts,
        point_columns=[column for column in properties.columns if column != "geometry"],
        polygon_columns=[tract_id_col, nta_id_col],
    )
    return pd.DataFrame(joined.drop(columns="geometry"))


def add_transit_context(properties: pd.DataFrame, subway_stops: pd.DataFrame | None) -> pd.DataFrame:
    """Compute nearest subway stop and simple line-count context."""

    if subway_stops is None or subway_stops.empty or properties.empty:
        output = properties.copy()
        output["nearest_subway_stop"] = pd.NA
        output["nearest_subway_distance_miles"] = pd.NA
        output["subway_lines_count"] = 0
        return output

    property_points = points_from_lon_lat(properties)
    subway_points = points_from_lon_lat(subway_stops)
    nearest = nearest_neighbor(
        origins=property_points,
        destinations=subway_points,
        origin_id_col="property_id",
        destination_id_col="subway_stop_id",
        destination_name_col="stop_name",
    )
    nearest = nearest.rename(
        columns={
            "stop_name": "nearest_subway_stop",
            "distance_miles": "nearest_subway_distance_miles",
        }
    )
    line_counts = subway_stops[["subway_stop_id", "lines"]].copy()
    line_counts["subway_lines_count"] = line_counts["lines"].fillna("").astype(str).str.split().str.len()
    nearest = nearest.merge(line_counts[["subway_stop_id", "subway_lines_count"]], on="subway_stop_id", how="left")
    return properties.merge(nearest, on="property_id", how="left")


def add_poi_context(properties: pd.DataFrame, poi: pd.DataFrame | None, radius_miles: float = 0.5) -> pd.DataFrame:
    """Count nearby user POIs."""

    if poi is None or poi.empty or properties.empty:
        output = properties.copy()
        output["poi_count_10min"] = 0
        output["poi_category_counts"] = [{} for _ in range(len(output))]
        return output

    property_points = points_from_lon_lat(properties)
    poi_points = points_from_lon_lat(poi)
    counts = count_points_within_radius(
        origins=property_points,
        points=poi_points,
        origin_id_col="property_id",
        point_category_col="category",
        radius_miles=radius_miles,
    ).rename(columns={"poi_count": "poi_count_10min"})
    return properties.merge(counts, on="property_id", how="left")


def add_scores(
    properties: pd.DataFrame,
    tract_features: pd.DataFrame | None = None,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Add component and total property scores."""

    output = properties.copy()
    if tract_features is not None and not tract_features.empty and "tract_id" in output.columns:
        output = output.merge(tract_features, on="tract_id", how="left")

    output["neighborhood_score"] = output.apply(neighborhood_score, axis=1)
    output["mobility_score"] = output.apply(
        lambda row: mobility_score(row.get("nearest_subway_distance_miles"), row.get("subway_lines_count")),
        axis=1,
    )
    output["personal_fit_score"] = output.apply(
        lambda row: personal_fit_score(row.get("poi_count_10min"), len(row.get("poi_category_counts") or {})),
        axis=1,
    )
    output["property_fit_score"] = output.apply(
        lambda row: property_fit_score(
            row["neighborhood_score"],
            row["mobility_score"],
            row["personal_fit_score"],
            weights=weights,
        ),
        axis=1,
    )
    return output


def build_property_context(
    properties: pd.DataFrame,
    tracts,
    subway_stops: pd.DataFrame | None = None,
    poi: pd.DataFrame | None = None,
    tract_features: pd.DataFrame | None = None,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Build the property context fact table."""

    with_geography = attach_geography(properties, tracts)
    with_transit = add_transit_context(with_geography, subway_stops)
    with_poi = add_poi_context(with_transit, poi)
    return add_scores(with_poi, tract_features=tract_features, weights=weights)


def prepare_property_context_for_duckdb(context: pd.DataFrame) -> pd.DataFrame:
    """Coerce context output to the persisted DuckDB table shape."""

    output = context.copy()
    if "poi_category_counts" in output.columns:
        output["poi_category_counts"] = output["poi_category_counts"].apply(
            lambda value: json.dumps(value or {}, sort_keys=True)
        )

    for column in PROPERTY_CONTEXT_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA

    return output[PROPERTY_CONTEXT_COLUMNS]


def write_property_context(
    context: pd.DataFrame,
    duckdb_service: DuckDBService,
    table_name: str = "fct_property_context",
    schema: str = "gold",
) -> None:
    """Persist the property context fact table."""

    duckdb_service.write_dataframe(
        prepare_property_context_for_duckdb(context),
        table_name=table_name,
        schema=schema,
        if_exists="replace",
    )


def _read_table_or_empty(duckdb_service: DuckDBService, table_name: str) -> pd.DataFrame:
    """Read a DuckDB table, returning an empty dataframe if it does not exist."""

    try:
        return duckdb_service.query_df(f"SELECT * FROM {table_name}")
    except Exception:
        return pd.DataFrame()


def load_context_inputs(database_path: str | Path) -> dict[str, pd.DataFrame]:
    """Load persisted inputs needed to build property context."""

    with DuckDBService(database_path, read_only=True) as duckdb_service:
        return {
            "properties": _read_table_or_empty(duckdb_service, "gold.dim_property_listing"),
            "mapping": _read_table_or_empty(duckdb_service, "gold.dim_tract_to_nta"),
            "subway_stops": _read_table_or_empty(duckdb_service, "gold.dim_subway_stop"),
            "poi": _read_table_or_empty(duckdb_service, "gold.dim_user_poi"),
            "tract_features": _read_table_or_empty(duckdb_service, "gold.fct_tract_features"),
        }


def load_tract_geometries(
    tract_path: str | Path,
    mapping: pd.DataFrame,
    tract_id_col: str = "tract_id",
) -> gpd.GeoDataFrame:
    """Load tract polygons and attach NTA mapping attributes."""

    tracts = gpd.read_file(tract_path)
    if tract_id_col not in tracts.columns:
        raise ValueError(f"Missing tract id column in tract geometry file: {tract_id_col}")

    tracts = tracts.rename(columns={tract_id_col: "tract_id"})
    if not mapping.empty and {"tract_id", "nta_id"}.issubset(mapping.columns):
        mapping_cols = [column for column in ["tract_id", "nta_id", "nta_name"] if column in mapping.columns]
        tracts = tracts.merge(mapping[mapping_cols].drop_duplicates("tract_id"), on="tract_id", how="left")
    elif "nta_id" not in tracts.columns:
        tracts["nta_id"] = pd.NA
    return tracts


def run(
    database_path: str | Path,
    tract_path: str | Path,
    tract_id_col: str = "tract_id",
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Build and persist property context from DuckDB inputs and tract geometries."""

    inputs = load_context_inputs(database_path)
    tracts = load_tract_geometries(
        tract_path=tract_path,
        mapping=inputs["mapping"],
        tract_id_col=tract_id_col,
    )
    context = build_property_context(
        properties=inputs["properties"],
        tracts=tracts,
        subway_stops=inputs["subway_stops"],
        poi=inputs["poi"],
        tract_features=inputs["tract_features"],
        weights=weights,
    )

    with DuckDBService(database_path) as duckdb_service:
        write_property_context(context, duckdb_service)
    return prepare_property_context_for_duckdb(context)
