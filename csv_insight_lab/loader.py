"""Loading a CSV file safely.

Everything that can go wrong while *reading* a file lives here, so the rest of
the program can assume it has a valid pandas DataFrame to work with.

Instead of letting Python print a long traceback, every expected problem
(missing file, empty file, wrong encoding, broken rows) is turned into a
CSVLoadError with a message a person can act on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


class CSVLoadError(Exception):
    """Raised when a CSV file cannot be read. The message is shown to the user."""


@dataclass
class LoadResult:
    """What load_csv returns: the data plus notes about how it was read."""

    df: pd.DataFrame
    path: Path
    skipped_lines: list[list[str]] = field(default_factory=list)


def load_csv(
    path: str | Path,
    sep: str = ",",
    encoding: str = "utf-8-sig",
    skip_bad_lines: bool = False,
) -> LoadResult:
    """Read a CSV file into a DataFrame, or raise CSVLoadError with a clear reason.

    Args:
        path: location of the CSV file.
        sep: the character that separates columns (default: comma).
        encoding: text encoding. "utf-8-sig" reads normal UTF-8 and also strips
            the invisible "byte order mark" that Excel adds to some exports.
        skip_bad_lines: if True, rows with too many fields are skipped and
            recorded instead of stopping the whole load.
    """
    path = Path(path)

    if not path.exists():
        raise CSVLoadError(f"File not found: {path}")
    if path.is_dir():
        raise CSVLoadError(f"{path} is a folder, not a CSV file.")
    if path.stat().st_size == 0:
        raise CSVLoadError(f"{path} is empty (0 bytes), so there is nothing to analyse.")

    skipped: list[list[str]] = []

    def remember_bad_line(fields: list[str]) -> None:
        # pandas calls this for every row that has too many fields.
        # Returning None tells pandas to drop the row.
        skipped.append(fields)
        return None

    read_options = {"sep": sep, "encoding": encoding}
    if skip_bad_lines:
        # A Python function can only be used as on_bad_lines with the
        # (slower) "python" parsing engine.
        read_options.update(engine="python", on_bad_lines=remember_bad_line)

    try:
        df = pd.read_csv(path, **read_options)
    except pd.errors.EmptyDataError:
        raise CSVLoadError(f"{path} has no columns to read (the file is blank).") from None
    except pd.errors.ParserError as error:
        raise CSVLoadError(
            f"{path} has a row with the wrong number of fields.\n"
            f"  Details from the parser: {error}\n"
            "  Fix the row, or run again with --skip-bad-lines to skip such rows."
        ) from None
    except UnicodeDecodeError:
        raise CSVLoadError(
            f"{path} is not valid {encoding} text.\n"
            "  Try again with --encoding latin-1 (common for files saved by older software)."
        ) from None
    except LookupError:
        raise CSVLoadError(f"Unknown encoding name: {encoding!r}") from None

    return LoadResult(df=df, path=path, skipped_lines=skipped)
