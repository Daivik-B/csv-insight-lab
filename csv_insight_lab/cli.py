"""The command-line interface: reads arguments, runs the pipeline, reports errors.

Pipeline:  load_csv  ->  profile_dataframe  ->  text_report (+ optional HTML report)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .loader import CSVLoadError, load_csv
from .profiler import profile_dataframe
from .report import text_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv-insight",
        description="Get a quick, readable first look at a CSV dataset.",
    )
    parser.add_argument("csv_file", help="path to the CSV file to inspect")
    parser.add_argument("--sep", default=",", help="column separator (default: ',')")
    parser.add_argument("--encoding", default="utf-8-sig",
                        help="text encoding of the file (default: utf-8)")
    parser.add_argument("--skip-bad-lines", action="store_true",
                        help="skip rows with too many fields instead of stopping")
    parser.add_argument("--top", type=int, default=5, metavar="N",
                        help="how many common values to list per category column (default: 5)")
    parser.add_argument("--html", metavar="PATH",
                        help="also save an HTML report with charts to PATH")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the tool. Returns an exit code: 0 = success, 1 = the file could not be read."""
    args = build_parser().parse_args(argv)
    if args.top < 1:
        print("Error: --top must be 1 or more.", file=sys.stderr)
        return 1

    try:
        loaded = load_csv(args.csv_file, sep=args.sep, encoding=args.encoding,
                          skip_bad_lines=args.skip_bad_lines)
    except CSVLoadError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    profile = profile_dataframe(loaded.df, top=args.top)
    print(text_report(profile, source=args.csv_file, skipped_lines=len(loaded.skipped_lines)))

    if args.html:
        # Imported here so that people who only want the text report never
        # pay the start-up cost of loading matplotlib.
        from .html_report import write_html_report

        out = write_html_report(profile, loaded.df, Path(args.html), source=args.csv_file,
                                skipped_lines=len(loaded.skipped_lines))
        print(f"HTML report saved to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
