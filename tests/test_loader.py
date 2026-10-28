"""Tests for csv_insight_lab.loader.

Each test writes a tiny CSV into a temporary folder (pytest's tmp_path),
so the tests never depend on files outside the repository.
"""

import pytest

from csv_insight_lab.loader import CSVLoadError, load_csv


def write(tmp_path, name, text, encoding="utf-8"):
    file = tmp_path / name
    file.write_text(text, encoding=encoding)
    return file


def test_loads_a_normal_file(tmp_path):
    file = write(tmp_path, "ok.csv", "name,score\nAsha,8\nRavi,9\n")
    result = load_csv(file)
    assert list(result.df.columns) == ["name", "score"]
    assert len(result.df) == 2
    assert result.skipped_lines == []


def test_missing_file_gives_clear_error(tmp_path):
    with pytest.raises(CSVLoadError, match="File not found"):
        load_csv(tmp_path / "does_not_exist.csv")


def test_folder_instead_of_file(tmp_path):
    with pytest.raises(CSVLoadError, match="is a folder"):
        load_csv(tmp_path)


def test_zero_byte_file(tmp_path):
    file = write(tmp_path, "empty.csv", "")
    with pytest.raises(CSVLoadError, match="empty"):
        load_csv(file)


def test_blank_lines_only(tmp_path):
    file = write(tmp_path, "blank.csv", "\n\n\n")
    with pytest.raises(CSVLoadError, match="no columns"):
        load_csv(file)


def test_header_only_file_loads_with_zero_rows(tmp_path):
    file = write(tmp_path, "header.csv", "a,b,c\n")
    result = load_csv(file)
    assert list(result.df.columns) == ["a", "b", "c"]
    assert len(result.df) == 0


def test_malformed_row_stops_with_hint(tmp_path):
    file = write(tmp_path, "bad.csv", "a,b\n1,2\n3,4,5\n6,7\n")
    with pytest.raises(CSVLoadError, match="--skip-bad-lines"):
        load_csv(file)


def test_malformed_row_can_be_skipped_and_is_recorded(tmp_path):
    file = write(tmp_path, "bad.csv", "a,b\n1,2\n3,4,5\n6,7\n")
    result = load_csv(file, skip_bad_lines=True)
    assert len(result.df) == 2
    assert result.skipped_lines == [["3", "4", "5"]]


def test_excel_byte_order_mark_is_removed(tmp_path):
    file = write(tmp_path, "bom.csv", "﻿name,score\nAsha,8\n")
    result = load_csv(file)
    assert result.df.columns[0] == "name"  # not "﻿name"


def test_wrong_encoding_suggests_latin1(tmp_path):
    file = tmp_path / "latin.csv"
    file.write_bytes("city\nM\xfcnchen\n".encode("latin-1"))
    with pytest.raises(CSVLoadError, match="latin-1"):
        load_csv(file)
    # ...and following the hint works:
    assert load_csv(file, encoding="latin-1").df.iloc[0, 0] == "München"


def test_custom_separator(tmp_path):
    file = write(tmp_path, "semi.csv", "a;b\n1;2\n")
    assert list(load_csv(file, sep=";").df.columns) == ["a", "b"]
