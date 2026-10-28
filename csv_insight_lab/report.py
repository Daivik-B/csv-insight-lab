"""Presentation: turning a DatasetProfile into a readable text report.

The text report uses plain ASCII characters only (no arrows or box-drawing
symbols), so it prints correctly even in older Windows terminals.
"""

from __future__ import annotations

from .profiler import ColumnProfile, DatasetProfile


def fmt_number(value: float) -> str:
    """1234.5678 -> '1,234.57'; 12.0 -> '12'. Avoids printing '-0.00'."""
    if value != value:  # NaN is the only value not equal to itself
        return "-"
    if float(value).is_integer():
        return f"{int(value):,}"
    text = f"{value:,.2f}"
    return "0.00" if text == "-0.00" else text


def format_table(headers: list[str], rows: list[list[str]], indent: str = "  ") -> str:
    """Align columns by padding each cell to the widest value in its column."""
    widths = [max(len(str(cell)) for cell in column) for column in zip(headers, *rows)]

    def line(cells):
        return indent + "  ".join(str(c).ljust(w) for c, w in zip(cells, widths)).rstrip()

    divider = indent + "  ".join("-" * w for w in widths)
    return "\n".join([line(headers), divider] + [line(r) for r in rows])


def describe_duplicates(profile: DatasetProfile, limit: int = 5) -> str:
    if profile.duplicate_rows == 0:
        return "0"
    shown = ", ".join(str(n) for n in profile.duplicate_row_numbers[:limit])
    more = " ..." if profile.duplicate_rows > limit else ""
    return f"{profile.duplicate_rows}  (data rows {shown}{more})"


def column_rows(columns: list[ColumnProfile]) -> list[list[str]]:
    return [[str(i), c.name, c.kind, c.dtype, f"{c.missing} ({c.missing_pct:g}%)", str(c.unique)]
            for i, c in enumerate(columns, start=1)]


def text_report(profile: DatasetProfile, source: str, skipped_lines: int = 0) -> str:
    """Build the full console report as one string."""
    title = f"CSV Insight Lab - report for {source}"
    parts = [title, "=" * len(title), ""]

    parts += [
        "OVERVIEW",
        f"  Rows            {profile.rows:,}",
        f"  Columns         {profile.columns:,}",
        f"  Missing cells   {profile.missing_cells:,} of {profile.total_cells:,} ({profile.missing_pct:g}%)",
        f"  Duplicate rows  {describe_duplicates(profile)}",
    ]
    if skipped_lines:
        parts.append(f"  Skipped lines   {skipped_lines} (malformed rows left out)")
    if profile.rows == 0:
        parts.append("  The file has column headers but no data rows.")

    parts += ["", "COLUMNS",
              format_table(["#", "Column", "Kind", "Type", "Missing", "Unique"],
                           column_rows(profile.column_profiles))]

    numeric = profile.columns_of_kind("numeric")
    if numeric:
        keys = ["count", "mean", "std", "min", "median", "max"]
        rows = [[c.name] + [fmt_number(c.numeric_summary.get(k, float("nan"))) for k in keys]
                for c in numeric]
        parts += ["", "NUMERIC COLUMNS",
                  format_table(["Column", "Count", "Mean", "Std", "Min", "Median", "Max"], rows)]

    grouped = profile.columns_of_kind("categorical") + profile.columns_of_kind("boolean")
    if grouped:
        parts += ["", "MOST COMMON VALUES"]
        for c in grouped:
            parts.append(f"  {c.name} ({c.unique} distinct)")
            for value, count in c.top_values:
                share = 100 * count / profile.rows if profile.rows else 0
                parts.append(f"    {value:<20} {count:>6,}  {share:5.1f}%")

    dates = profile.columns_of_kind("datetime")
    if dates:
        parts += ["", "DATES"]
        for c in dates:
            start, end = (d[:10] for d in c.date_range)
            parts.append(f"  {c.name}: {start} to {end}")

    notes = [(c.name, note) for c in profile.column_profiles for note in c.notes]
    parts += ["", "WORTH A SECOND LOOK"]
    if notes or profile.duplicate_rows:
        if profile.duplicate_rows:
            parts.append(f"  - {profile.duplicate_rows} row(s) are exact copies of an earlier row.")
        parts += [f"  - {name}: {note}" for name, note in notes]
    else:
        parts.append("  Nothing unusual found.")

    return "\n".join(parts) + "\n"
