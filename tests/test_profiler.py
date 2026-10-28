"""Tests for csv_insight_lab.profiler. Small DataFrames with answers we can check by hand."""

import numpy as np
import pandas as pd
import pytest

from csv_insight_lab.profiler import classify_column, profile_dataframe


@pytest.fixture
def orders():
    return pd.DataFrame({
        "order_id": [1, 2, 3, 4, 4],
        "item": ["Tea", "Dosa", "Tea", "Tea", "Tea"],
        "price": [10.0, 40.0, np.nan, 10.0, 10.0],
        "date": ["2026-10-01", "2026-10-02", "2026-10-02", "2026-10-03", "2026-10-03"],
    })


def test_shape_and_missing_cells(orders):
    profile = profile_dataframe(orders)
    assert (profile.rows, profile.columns) == (5, 4)
    assert profile.total_cells == 20
    assert profile.missing_cells == 1
    assert profile.missing_pct == 5.0


def test_duplicate_rows_are_counted_and_located():
    df = pd.DataFrame({"a": [1, 2, 1, 1], "b": ["x", "y", "x", "x"]})
    profile = profile_dataframe(df)
    assert profile.duplicate_rows == 2          # rows 3 and 4 repeat row 1
    assert profile.duplicate_row_numbers == [3, 4]


def test_column_kinds(orders):
    kinds = {c.name: c.kind for c in profile_dataframe(orders).column_profiles}
    assert kinds == {"order_id": "numeric", "item": "categorical",
                     "price": "numeric", "date": "datetime"}


def test_numeric_summary_matches_hand_calculation(orders):
    price = next(c for c in profile_dataframe(orders).column_profiles if c.name == "price")
    summary = price.numeric_summary
    assert summary["count"] == 4             # the missing value is not counted
    assert summary["mean"] == pytest.approx(17.5)
    assert summary["min"] == 10.0 and summary["max"] == 40.0
    assert price.missing == 1 and price.missing_pct == 20.0


def test_category_frequencies_are_sorted(orders):
    item = next(c for c in profile_dataframe(orders).column_profiles if c.name == "item")
    assert item.top_values == [("Tea", 4), ("Dosa", 1)]


def test_date_range(orders):
    date = next(c for c in profile_dataframe(orders).column_profiles if c.name == "date")
    assert date.date_range == ("2026-10-01T00:00:00", "2026-10-03T00:00:00")


def test_ambiguous_dates_are_not_guessed():
    # 03/04/2026 could be 3 April or 4 March, so it stays text.
    series = pd.Series(["03/04/2026", "05/06/2026", "07/08/2026"], name="d")
    assert classify_column(series) != "datetime"


def test_unique_text_is_not_treated_as_categories():
    names = pd.Series([f"student_{i}" for i in range(30)], name="name")
    profile = profile_dataframe(names.to_frame()).column_profiles[0]
    assert profile.kind == "text"
    assert any("ID column" in note for note in profile.notes)


def test_empty_and_constant_columns_get_notes():
    df = pd.DataFrame({"blank": [np.nan, np.nan, np.nan], "same": ["A", "A", "A"]})
    blank, same = profile_dataframe(df).column_profiles
    assert blank.kind == "empty" and "Every value is missing." in blank.notes
    assert any("one distinct value" in note for note in same.notes)


def test_boolean_column():
    df = pd.DataFrame({"paid": [True, False, True, True]})
    paid = profile_dataframe(df).column_profiles[0]
    assert paid.kind == "boolean"
    assert paid.top_values == [("True", 3), ("False", 1)]


def test_header_only_dataframe():
    profile = profile_dataframe(pd.DataFrame(columns=["a", "b"]))
    assert profile.rows == 0 and profile.columns == 2
    assert profile.missing_pct == 0.0  # no division-by-zero crash
    assert all(c.kind == "empty" for c in profile.column_profiles)
