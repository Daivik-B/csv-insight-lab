"""Tests for the text report, the HTML report and the command-line interface."""

from pathlib import Path

import pandas as pd

from csv_insight_lab.cli import main
from csv_insight_lab.html_report import build_html
from csv_insight_lab.profiler import profile_dataframe
from csv_insight_lab.report import fmt_number, text_report

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_canteen_orders.csv"


def test_fmt_number():
    assert fmt_number(1234.5678) == "1,234.57"
    assert fmt_number(12.0) == "12"
    assert fmt_number(-0.001) == "0.00"
    assert fmt_number(float("nan")) == "-"


def test_text_report_has_every_section():
    df = pd.DataFrame({"n": [1, 2, 2, 3], "c": ["a", "b", "b", "b"], "d": ["2026-01-01"] * 4})
    report = text_report(profile_dataframe(df), source="x.csv")
    for heading in ["OVERVIEW", "COLUMNS", "NUMERIC COLUMNS", "MOST COMMON VALUES",
                    "DATES", "WORTH A SECOND LOOK"]:
        assert heading in report
    assert report.isascii()  # safe for any terminal


def test_html_escapes_text_from_the_csv():
    df = pd.DataFrame({"<script>alert(1)</script>": ["x", "x", "y"]})
    page = build_html(profile_dataframe(df), df, source="evil.csv")
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_cli_on_sample_file(capsys, tmp_path):
    out = tmp_path / "report.html"
    assert main([str(SAMPLE), "--html", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "Duplicate rows  3" in printed
    page = out.read_text(encoding="utf-8")
    assert page.count("<img") >= 3  # missing-values chart, histograms, category charts


def test_cli_missing_file_returns_error_code(capsys):
    assert main(["no_such_file.csv"]) == 1
    assert "File not found" in capsys.readouterr().err


def test_cli_header_only_file(capsys, tmp_path):
    file = tmp_path / "header.csv"
    file.write_text("a,b\n", encoding="utf-8")
    assert main([str(file)]) == 0
    assert "no data rows" in capsys.readouterr().out


def test_cli_rejects_top_below_one(capsys):
    assert main([str(SAMPLE), "--top", "0"]) == 1


def test_small_whole_number_columns_are_detected():
    from csv_insight_lab.charts import is_few_whole_numbers
    assert is_few_whole_numbers(pd.Series([1, 2, 3, 2, None]))   # e.g. quantity with a gap
    assert not is_few_whole_numbers(pd.Series([1.5, 2.25, 3.0]))  # decimals -> histogram
    assert not is_few_whole_numbers(pd.Series(range(100)))        # too many values
