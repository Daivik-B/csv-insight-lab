"""A self-contained HTML report: one file, charts embedded, no internet needed.

Charts are embedded as base64 text inside <img> tags, so the report can be
emailed or opened offline as a single file.

Every value that comes from the CSV (column names, category values) is passed
through html.escape(). A CSV could contain text like "<script>"; escaping
makes the browser show it as text instead of running it.
"""

from __future__ import annotations

import base64
import html
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import __version__
from .charts import histogram, horizontal_bars, is_few_whole_numbers, value_bars
from .profiler import DatasetProfile
from .report import describe_duplicates, fmt_number

MAX_CHARTS_PER_KIND = 6

STYLE = """
body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0;
       background: #F7F6F2; color: #1B2433; line-height: 1.5; }
main { max-width: 920px; margin: 0 auto; padding: 32px 20px 64px; }
h1 { font-size: 1.6rem; margin: 0 0 4px; }
h2 { font-size: 1.05rem; margin: 36px 0 12px; padding-top: 12px; border-top: 1px solid #D9D6CE; }
.meta { color: #5B6472; font-size: .9rem; margin: 0; }
.overview { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.tile { background: #fff; border: 1px solid #E4E2DC; border-radius: 8px; padding: 12px 14px; }
.tile span { display: block; color: #5B6472; font-size: .8rem; }
.tile strong { font-size: 1.15rem; }
table { border-collapse: collapse; width: 100%; background: #fff; font-size: .88rem; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #ECEAE4; }
th { color: #5B6472; font-weight: 600; background: #FBFAF7; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.charts { margin-top: 14px; display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); align-items: start; }
th.num { text-align: right; }
figure { margin: 0; background: #fff; border: 1px solid #E4E2DC; border-radius: 8px; padding: 8px; }
figure img { width: 100%; height: auto; display: block; }
ul.notes li { margin-bottom: 4px; }
.scroll { overflow-x: auto; }
"""


def _img(png: bytes, alt: str) -> str:
    data = base64.b64encode(png).decode("ascii")
    return (f'<figure><img src="data:image/png;base64,{data}" alt="{html.escape(alt)}">'
            "</figure>")


def _table(headers: list[str], rows: list[list[str]], numeric_from: int = 99) -> str:
    head = "".join(f'<th class="num">{html.escape(h)}</th>' if i >= numeric_from
                   else f"<th>{html.escape(h)}</th>" for i, h in enumerate(headers))
    body = ""
    for row in rows:
        cells = "".join(
            f'<td class="num">{html.escape(c)}</td>' if i >= numeric_from else f"<td>{html.escape(c)}</td>"
            for i, c in enumerate(row))
        body += f"<tr>{cells}</tr>"
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def build_html(profile: DatasetProfile, df: pd.DataFrame, source: str, skipped_lines: int = 0) -> str:
    esc = html.escape
    tiles = [("Rows", f"{profile.rows:,}"), ("Columns", f"{profile.columns:,}"),
             ("Missing cells", f"{profile.missing_cells:,} ({profile.missing_pct:g}%)"),
             ("Duplicate rows", f"{profile.duplicate_rows:,}")]
    if skipped_lines:
        tiles.append(("Skipped malformed lines", f"{skipped_lines:,}"))
    sections = ['<div class="overview">' + "".join(
        f'<div class="tile"><span>{esc(k)}</span><strong>{esc(v)}</strong></div>' for k, v in tiles)
        + "</div>"]
    if profile.duplicate_rows:
        sections.append(f'<p class="meta">Duplicates: {esc(describe_duplicates(profile))}. '
                        "Row 1 is the first row after the header.</p>")

    sections.append("<h2>Columns</h2>" + _table(
        ["#", "Column", "Kind", "Type", "Missing", "Unique"],
        [[str(i), c.name, c.kind, c.dtype, f"{c.missing} ({c.missing_pct:g}%)", str(c.unique)]
         for i, c in enumerate(profile.column_profiles, start=1)], numeric_from=4))

    missing = [c for c in profile.column_profiles if c.missing]
    if missing:
        missing.sort(key=lambda c: c.missing, reverse=True)
        sections.append('<h2>Missing values</h2><div class="charts">' + _img(
            horizontal_bars([c.name for c in missing], [c.missing for c in missing],
                            "Missing values per column", "Missing cells"),
            "Bar chart of missing values per column; exact counts are in the Columns table.") + "</div>")

    numeric = profile.columns_of_kind("numeric")
    if numeric:
        keys = ["count", "mean", "std", "min", "q1", "median", "q3", "max"]
        sections.append("<h2>Numeric columns</h2>" + _table(
            ["Column", "Count", "Mean", "Std", "Min", "25%", "Median", "75%", "Max"],
            [[c.name] + [fmt_number(c.numeric_summary.get(k, float("nan"))) for k in keys]
             for c in numeric], numeric_from=1))
        # Skip ID-like columns: a histogram of order numbers says nothing.
        plottable = [c for c in numeric if not any("ID column" in n for n in c.notes)]
        charts = []
        for c in plottable[:MAX_CHARTS_PER_KIND]:
            if is_few_whole_numbers(df[c.name]):
                png = value_bars(df[c.name], f"{c.name}: rows per value")
            else:
                png = histogram(df[c.name], f"Distribution of {c.name}")
            charts.append(_img(png, f"Chart of {c.name}; exact figures are in the table above."))
        if charts:
            sections.append('<div class="charts">' + "".join(charts) + "</div>")

    categorical = profile.columns_of_kind("categorical") + profile.columns_of_kind("boolean")
    if categorical:
        charts = []
        for c in categorical[:MAX_CHARTS_PER_KIND]:
            labels = [v for v, _ in c.top_values]
            counts = [n for _, n in c.top_values]
            charts.append(_img(
                horizontal_bars(labels, counts, f"{c.name}: most common values", "Rows"),
                f"Bar chart of the most common values in {c.name}: "
                + ", ".join(f"{v} {n}" for v, n in c.top_values)))
        sections.append('<h2>Most common values</h2><div class="charts">' + "".join(charts) + "</div>")

    dates = profile.columns_of_kind("datetime")
    if dates:
        sections.append("<h2>Dates</h2>" + _table(
            ["Column", "Earliest", "Latest"],
            [[c.name, c.date_range[0][:10], c.date_range[1][:10]] for c in dates]))

    notes = [f"{c.name}: {n}" for c in profile.column_profiles for n in c.notes]
    if profile.duplicate_rows:
        notes.insert(0, f"{profile.duplicate_rows} row(s) are exact copies of an earlier row.")
    sections.append("<h2>Worth a second look</h2>" + (
        '<ul class="notes">' + "".join(f"<li>{esc(n)}</li>" for n in notes) + "</ul>"
        if notes else "<p>Nothing unusual found.</p>"))

    created = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CSV Insight Lab report - {esc(source)}</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>CSV Insight Lab report</h1>
<p class="meta">File: {esc(source)} &middot; generated {created} &middot; CSV Insight Lab {__version__}</p>
{''.join(sections)}
</main>
</body>
</html>
"""


def write_html_report(profile: DatasetProfile, df: pd.DataFrame, path: Path, source: str,
                      skipped_lines: int = 0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_html(profile, df, source, skipped_lines), encoding="utf-8")
    return path
