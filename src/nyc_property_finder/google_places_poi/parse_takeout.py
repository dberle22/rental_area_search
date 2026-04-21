"""Google Takeout saved-list parsing for the Places POI workflow."""

from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path
from urllib.parse import unquote

import pandas as pd

from nyc_property_finder.google_places_poi.config import DEFAULT_SEARCH_CONTEXT, SOURCE_SYSTEM


TAKEOUT_COLUMNS = ("Title", "Note", "URL", "Tags", "Comment")


def parse_google_places_saved_list_csv(
    path: str | Path,
    search_context: str = DEFAULT_SEARCH_CONTEXT,
    source_list_name: str | None = None,
) -> pd.DataFrame:
    """Parse one Google Takeout saved-list CSV for the v2 Places pipeline."""

    path = Path(path)
    rows = _read_takeout_csv(path)
    source_list_name = source_list_name or path.stem

    # Takeout exports can omit user-metadata columns when they are empty. Add
    # them here so downstream pipeline steps always see the same contract.
    for column in TAKEOUT_COLUMNS:
        if column not in rows.columns:
            rows[column] = ""

    output = rows.loc[:, TAKEOUT_COLUMNS].copy()
    output["input_title"] = output["Title"].fillna("").astype(str).str.strip()
    # Google includes a blank example-looking row in some CSV exports; skip it
    # before creating stable source IDs.
    output = output[output["input_title"] != ""].copy()
    output["source_url"] = output["URL"].fillna("").astype(str).map(lambda value: unquote(value.strip()))
    output["note"] = output["Note"].fillna("").astype(str).str.strip()
    output["tags"] = output["Tags"].fillna("").astype(str).str.strip()
    output["comment"] = output["Comment"].fillna("").astype(str).str.strip()
    output["source_system"] = SOURCE_SYSTEM
    output["source_file"] = path.name
    output["source_list_name"] = source_list_name
    # Categories are intentionally list-derived in v2. A proper category
    # dimension can replace this later without changing raw Takeout parsing.
    output["category"] = clean_list_category(source_list_name)
    output["search_query"] = output["input_title"].map(lambda title: build_search_query(title, search_context))
    output["source_record_id"] = output.apply(
        lambda row: _stable_source_record_id(
            source_system=row["source_system"],
            source_file=row["source_file"],
            source_list_name=row["source_list_name"],
            input_title=row["input_title"],
            source_url=row["source_url"],
        ),
        axis=1,
    )
    return output[
        [
            "source_record_id",
            "source_system",
            "source_file",
            "source_list_name",
            "category",
            "input_title",
            "note",
            "tags",
            "comment",
            "source_url",
            "search_query",
        ]
    ]


def build_search_query(title: str, search_context: str = DEFAULT_SEARCH_CONTEXT) -> str:
    """Build the first-pass low-cost text search query."""

    title = " ".join(str(title).split())
    search_context = " ".join(str(search_context).split())
    if not search_context:
        return title
    return f"{title} {search_context}".strip()


def clean_list_category(list_name: str) -> str:
    """Convert a saved-list name into an initial category token."""

    cleaned = str(list_name).strip().lower()
    cleaned = re.sub(r"^new york\s*-\s*", "", cleaned)
    cleaned = re.sub(r"\bnyc\b", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = cleaned.strip("_")
    return cleaned or "other"


def _read_takeout_csv(path: Path) -> pd.DataFrame:
    # Some Google exports include a first descriptive line before the real CSV
    # header. Try the normal header first, then a one-line offset.
    rows = pd.read_csv(path, comment=None, skip_blank_lines=True)
    if "Title" not in rows.columns:
        rows = pd.read_csv(path, skiprows=1, skip_blank_lines=True)

    if "Title" not in rows.columns:
        raise ValueError(f"Google Maps CSV missing Title column: {path}")
    return rows


def _stable_source_record_id(
    source_system: str,
    source_file: str,
    source_list_name: str,
    input_title: str,
    source_url: str,
) -> str:
    # The source row ID is pre-Google matching identity. It lets dry runs and
    # caches recognize the same input row before a place_id exists.
    key = "|".join(
        [
            source_system.strip().lower(),
            source_file.strip().lower(),
            source_list_name.strip().lower(),
            input_title.strip().lower(),
            source_url.strip(),
        ]
    )
    return f"src_{sha256(key.encode('utf-8')).hexdigest()[:16]}"
