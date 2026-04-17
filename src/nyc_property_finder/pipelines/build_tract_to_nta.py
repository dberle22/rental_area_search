"""Build tract-to-NTA geography mapping."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from nyc_property_finder.services.duckdb_service import DuckDBService
from nyc_property_finder.utils.geo import spatial_join_centroids_to_polygons


def load_shapefile(path: str | Path) -> gpd.GeoDataFrame:
    """Load a shapefile or any vector file supported by GeoPandas."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Geometry file does not exist: {path}")
    return gpd.read_file(path)


def build_tract_to_nta(
    tract_path: str | Path,
    nta_path: str | Path,
    tract_id_col: str = "tract_id",
    nta_id_col: str = "nta_id",
    nta_name_col: str = "nta_name",
) -> gpd.GeoDataFrame:
    """Assign census tracts to NTAs using tract centroids."""

    tracts = load_shapefile(tract_path)
    ntas = load_shapefile(nta_path)

    required_tract_cols = {tract_id_col}
    required_nta_cols = {nta_id_col, nta_name_col}
    missing_tract_cols = required_tract_cols.difference(tracts.columns)
    missing_nta_cols = required_nta_cols.difference(ntas.columns)
    if missing_tract_cols:
        raise ValueError(f"Missing tract columns: {sorted(missing_tract_cols)}")
    if missing_nta_cols:
        raise ValueError(f"Missing NTA columns: {sorted(missing_nta_cols)}")

    mapping = spatial_join_centroids_to_polygons(
        source_polygons=tracts,
        target_polygons=ntas,
        source_id_col=tract_id_col,
        target_columns=[nta_id_col, nta_name_col],
    )
    return mapping.rename(
        columns={
            tract_id_col: "tract_id",
            nta_id_col: "nta_id",
            nta_name_col: "nta_name",
        }
    )[["tract_id", "nta_id", "nta_name", "geometry"]]


def write_tract_to_nta(
    mapping: gpd.GeoDataFrame,
    duckdb_service: DuckDBService,
    table_name: str = "dim_tract_to_nta",
    schema: str = "gold",
) -> None:
    """Persist the mapping to DuckDB.

    DuckDB does not need to own geometry for the first starter version. We store
    WKT for portability and keep geospatial operations in GeoPandas.
    """

    output = mapping.copy()
    output["geometry_wkt"] = output.geometry.to_wkt()
    duckdb_service.write_dataframe(
        dataframe=output.drop(columns="geometry"),
        table_name=table_name,
        schema=schema,
        if_exists="replace",
    )


def run(
    tract_path: str | Path,
    nta_path: str | Path,
    database_path: str | Path,
) -> gpd.GeoDataFrame:
    """Build and store tract-to-NTA mapping."""

    mapping = build_tract_to_nta(tract_path=tract_path, nta_path=nta_path)
    with DuckDBService(database_path) as duckdb_service:
        write_tract_to_nta(mapping, duckdb_service)
    return mapping
