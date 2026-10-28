"""Charts for the HTML report, drawn with matplotlib and returned as PNG bytes.

Every chart here shows a single series, so it uses one colour and no legend;
the chart title says what is plotted. Exact numbers are always available in
the tables of the report, so the charts are a visual aid, not the only source.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")  # draw to memory; no window needed (works on servers too)
import matplotlib.pyplot as plt  # noqa: E402  (must come after matplotlib.use)
import pandas as pd  # noqa: E402

BAR = "#2448E0"      # cobalt, the single data colour
INK = "#1B2433"      # titles
MUTED = "#5B6472"    # axis labels and ticks
GRID = "#E4E2DC"     # recessive hairline grid
SURFACE = "#FFFFFF"


def _new_axes(title: str, width: float = 4.8, height: float = 2.9):
    fig, ax = plt.subplots(figsize=(width, height), dpi=144)
    fig.patch.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=10.5, color=INK, fontweight="bold", pad=10)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.set_axisbelow(True)
    return fig, ax


def _to_png(fig) -> bytes:
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", facecolor=SURFACE)
    plt.close(fig)  # free memory; important when drawing many charts
    return buffer.getvalue()


def horizontal_bars(labels: list[str], values: list[float], title: str, xlabel: str) -> bytes:
    """Bars sorted so the largest value is at the top."""
    height = max(2.0, 0.4 * len(labels) + 1.1)
    fig, ax = _new_axes(title, height=height)
    positions = range(len(labels))[::-1]  # first label drawn at the top
    ax.barh(list(positions), values, height=0.55, color=BAR)
    ax.set_yticks(list(positions), labels)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
    for y, value in zip(positions, values):  # value at the tip of each bar
        ax.text(value, y, f"  {value:,.0f}", va="center", fontsize=8, color=INK)
    ax.set_xlim(0, max(values) * 1.15 if values else 1)
    return _to_png(fig)


def histogram(series: pd.Series, title: str) -> bytes:
    """Distribution of a numeric column. White edges keep touching bars distinct."""
    fig, ax = _new_axes(title)
    values = series.dropna()
    bins = min(20, max(1, int(values.nunique())))
    ax.hist(values, bins=bins, color=BAR, edgecolor=SURFACE, linewidth=2)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_ylabel("Rows", color=MUTED, fontsize=8.5)
    return _to_png(fig)


def is_few_whole_numbers(series: pd.Series, limit: int = 12) -> bool:
    """True for columns like quantity (1, 2, 3) or rating (1-5).

    A histogram would invent bins such as 1.00-1.67 for these, so they are
    drawn as one bar per value instead.
    """
    values = series.dropna()
    return (not values.empty and values.nunique() <= limit
            and bool((values % 1 == 0).all()))


def value_bars(series: pd.Series, title: str) -> bytes:
    """One column per distinct whole-number value, in numeric order."""
    counts = series.dropna().value_counts().sort_index()
    fig, ax = _new_axes(title)
    positions = range(len(counts))
    ax.bar(list(positions), counts.to_numpy(), width=0.55, color=BAR)
    ax.set_xticks(list(positions), [f"{v:g}" for v in counts.index])
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_ylabel("Rows", color=MUTED, fontsize=8.5)
    for x, n in zip(positions, counts.to_numpy()):  # value on each column cap
        ax.text(x, n, f"{n:,}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_ylim(0, counts.max() * 1.15)
    return _to_png(fig)
