"""Simple starter scoring functions."""

from __future__ import annotations

import pandas as pd


def clamp_score(value: float, min_value: float = 0, max_value: float = 100) -> float:
    """Constrain a score to a readable 0-100 range."""

    return float(max(min_value, min(max_value, value)))


def neighborhood_score(row: pd.Series) -> float:
    """Compute a placeholder neighborhood score from tract/NTA features."""

    income_component = min(float(row.get("median_income", 0) or 0) / 150_000 * 40, 40)
    education_component = float(row.get("pct_bachelors_plus", 0) or 0) * 30
    safety_component = max(0, 30 - float(row.get("crime_rate_proxy", 0) or 0) * 3)
    return clamp_score(income_component + education_component + safety_component)


def mobility_score(nearest_subway_distance_miles: float | None, subway_lines_count: int | None = 0) -> float:
    """Score mobility from subway proximity and line access."""

    if nearest_subway_distance_miles is None:
        return 0.0
    proximity_component = max(0, 75 - nearest_subway_distance_miles * 100)
    line_component = min(int(subway_lines_count or 0) * 5, 25)
    return clamp_score(proximity_component + line_component)


def personal_fit_score(poi_count: int | None, preferred_category_matches: int | None = 0) -> float:
    """Score fit from nearby saved places."""

    poi_component = min(int(poi_count or 0) * 8, 70)
    category_component = min(int(preferred_category_matches or 0) * 10, 30)
    return clamp_score(poi_component + category_component)


def property_fit_score(
    neighborhood: float,
    mobility: float,
    personal_fit: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Combine component scores into one property fit score."""

    weights = weights or {"neighborhood": 0.40, "mobility": 0.25, "personal_fit": 0.35}
    return clamp_score(
        neighborhood * weights["neighborhood"]
        + mobility * weights["mobility"]
        + personal_fit * weights["personal_fit"]
    )
