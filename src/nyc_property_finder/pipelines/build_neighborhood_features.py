"""Build starter neighborhood feature tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nyc_property_finder.services.duckdb_service import DuckDBService


TRACT_FEATURE_COLUMNS = [
    "tract_id",
    "median_income",
    "median_rent",
    "median_home_value",
    "pct_bachelors_plus",
    "median_age",
    "crime_rate_proxy",
]


def build_acs_features(acs_dataframe: pd.DataFrame | None = None) -> pd.DataFrame:
    """Create tract-level ACS features.

    TODO: Replace placeholder column mapping with Census API/table-specific
    transforms after source fields are finalized.
    """

    if acs_dataframe is None or acs_dataframe.empty:
        return pd.DataFrame(columns=TRACT_FEATURE_COLUMNS)

    output = acs_dataframe.copy()
    for column in TRACT_FEATURE_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    return output[TRACT_FEATURE_COLUMNS]


def add_crime_proxy(features: pd.DataFrame, crime_dataframe: pd.DataFrame | None = None) -> pd.DataFrame:
    """Add a simple crime proxy to tract features."""

    output = features.copy()
    if crime_dataframe is None or crime_dataframe.empty:
        output["crime_rate_proxy"] = output["crime_rate_proxy"].fillna(0)
        return output

    # TODO: Spatially join incidents to tracts and normalize by population.
    crime_counts = crime_dataframe.groupby("tract_id").size().reset_index(name="crime_rate_proxy")
    output = output.drop(columns=["crime_rate_proxy"], errors="ignore").merge(crime_counts, on="tract_id", how="left")
    output["crime_rate_proxy"] = output["crime_rate_proxy"].fillna(0)
    return output[TRACT_FEATURE_COLUMNS]


def build_neighborhood_features(
    acs_dataframe: pd.DataFrame | None = None,
    crime_dataframe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build tract-level neighborhood features from ACS and crime inputs."""

    features = build_acs_features(acs_dataframe)
    return add_crime_proxy(features, crime_dataframe)


def write_neighborhood_features(
    features: pd.DataFrame,
    duckdb_service: DuckDBService,
    table_name: str = "fct_tract_features",
    schema: str = "gold",
) -> None:
    """Persist tract feature table."""

    duckdb_service.write_dataframe(features, table_name=table_name, schema=schema, if_exists="replace")


def run(database_path: str | Path) -> pd.DataFrame:
    """Pipeline entry point using placeholder empty source data."""

    features = build_neighborhood_features()
    with DuckDBService(database_path) as duckdb_service:
        write_neighborhood_features(features, duckdb_service)
    return features
