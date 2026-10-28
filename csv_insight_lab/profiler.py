"""Profiling: turning a DataFrame into plain facts about the dataset.

This module never prints anything and never draws charts. It only calculates.
Keeping the calculations separate from the presentation (report.py) makes both
easier to test: the tests here check numbers, not formatting.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from pandas.api import types as ptypes

# A text column counts as "categorical" when it has at most this many distinct
# values AND values repeat a lot (see classify_column). 20 is a judgement call:
# small enough that a frequency table stays readable.
DEFAULT_MAX_CATEGORIES = 20

# Date detection only looks at this many values, so huge files stay fast.
DATE_SAMPLE_SIZE = 200


@dataclass
class ColumnProfile:
    name: str
    kind: str  # "numeric", "boolean", "datetime", "categorical", "text" or "empty"
    dtype: str  # the pandas data type, e.g. "int64", "float64", "str"
    missing: int
    missing_pct: float
    unique: int
    numeric_summary: dict[str, float] | None = None
    top_values: list[tuple[str, int]] | None = None
    date_range: tuple[str, str] | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class DatasetProfile:
    rows: int
    columns: int
    total_cells: int
    missing_cells: int
    duplicate_rows: int
    duplicate_row_numbers: list[int]  # 1-based: row 1 is the first data row
    column_profiles: list[ColumnProfile]

    @property
    def missing_pct(self) -> float:
        return percent(self.missing_cells, self.total_cells)

    def columns_of_kind(self, kind: str) -> list[ColumnProfile]:
        return [c for c in self.column_profiles if c.kind == kind]


def percent(part: int, whole: int) -> float:
    """part / whole as a percentage, safe when whole is 0."""
    return 0.0 if whole == 0 else round(100 * part / whole, 1)


def parse_iso_dates(values: pd.Series) -> pd.Series:
    """Parse text as ISO dates (2026-10-28 or 2026-10-28T09:30). Non-dates become NaT.

    Only the unambiguous ISO format is accepted on purpose: "03/04/2026"
    means 3 April in India but 4 March in the USA, so guessing would be wrong
    for someone.
    """
    return pd.to_datetime(values.astype(str), format="ISO8601", errors="coerce")


def looks_like_dates(non_null: pd.Series) -> bool:
    sample = non_null.head(DATE_SAMPLE_SIZE)
    return bool(parse_iso_dates(sample).notna().mean() >= 0.9)


def classify_column(series: pd.Series, max_categories: int = DEFAULT_MAX_CATEGORIES) -> str:
    """Decide what kind of data a column holds. The order of the checks matters."""
    non_null = series.dropna()
    if non_null.empty:
        return "empty"
    if ptypes.is_bool_dtype(series):
        return "boolean"  # checked before numeric, because pandas also treats bool as numeric
    if ptypes.is_numeric_dtype(series):
        return "numeric"
    if ptypes.is_datetime64_any_dtype(series) or looks_like_dates(non_null):
        return "datetime"
    distinct = non_null.nunique()
    if distinct <= max_categories and distinct <= 0.5 * len(non_null):
        return "categorical"
    return "text"


def looks_like_id(series: pd.Series, kind: str) -> bool:
    """IDs are whole numbers or text where (almost) every value is different.

    Decimal numbers are excluded on purpose: measurements such as 23.71 and
    23.74 are usually all different too, but they are data, not IDs.
    The 95% threshold tolerates a few duplicated rows in the file.
    """
    non_null = series.dropna()
    if len(non_null) < 2:
        return False
    is_candidate = kind == "text" or (kind == "numeric" and ptypes.is_integer_dtype(series))
    return is_candidate and non_null.nunique() / len(non_null) >= 0.95


def summarise_numbers(series: pd.Series) -> dict[str, float]:
    stats = series.describe()  # count, mean, std, min, 25%, 50%, 75%, max
    names = {"count": "count", "mean": "mean", "std": "std", "min": "min",
             "25%": "q1", "50%": "median", "75%": "q3", "max": "max"}
    return {nice: float(stats[raw]) for raw, nice in names.items() if raw in stats}


def profile_column(series: pd.Series, top: int = 5,
                   max_categories: int = DEFAULT_MAX_CATEGORIES) -> ColumnProfile:
    rows = len(series)
    non_null = series.dropna()
    kind = classify_column(series, max_categories)
    profile = ColumnProfile(
        name=str(series.name),
        kind=kind,
        dtype=str(series.dtype),
        missing=int(series.isna().sum()),
        missing_pct=percent(int(series.isna().sum()), rows),
        unique=int(non_null.nunique()),
    )

    if kind == "numeric":
        profile.numeric_summary = summarise_numbers(non_null)
    elif kind in ("categorical", "boolean"):
        counts = non_null.astype(str).value_counts().head(top)
        profile.top_values = [(str(value), int(n)) for value, n in counts.items()]
    elif kind == "datetime":
        dates = non_null if ptypes.is_datetime64_any_dtype(non_null) else parse_iso_dates(non_null)
        dates = dates.dropna()
        profile.date_range = (dates.min().isoformat(), dates.max().isoformat())

    # Plain-language observations that are worth a second look.
    if kind == "empty":
        profile.notes.append("Every value is missing.")
    elif profile.unique == 1:
        profile.notes.append("Only one distinct value, so this column tells you little.")
    elif looks_like_id(series, kind):
        if profile.unique == len(non_null):
            profile.notes.append("Every value is different. This may be an ID column.")
        else:
            profile.notes.append(f"Almost every value is different ({profile.unique} of "
                                 f"{len(non_null)}). This may be an ID column.")
    if kind != "empty" and profile.missing_pct >= 20:
        profile.notes.append(f"{profile.missing_pct}% of values are missing.")
    return profile


def profile_dataframe(df: pd.DataFrame, top: int = 5,
                      max_categories: int = DEFAULT_MAX_CATEGORIES) -> DatasetProfile:
    """Calculate everything the report needs about a dataset."""
    duplicated = df.duplicated(keep="first")  # True for the 2nd, 3rd... copy of a row
    positions = [i for i, is_dup in enumerate(duplicated) if is_dup]
    return DatasetProfile(
        rows=len(df),
        columns=len(df.columns),
        total_cells=int(df.size),
        missing_cells=int(df.isna().sum().sum()),
        duplicate_rows=len(positions),
        duplicate_row_numbers=[p + 1 for p in positions],
        column_profiles=[profile_column(df[c], top, max_categories) for c in df.columns],
    )
