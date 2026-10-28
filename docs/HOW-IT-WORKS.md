# How CSV Insight Lab works

A walkthrough of the code for anyone reading it for the first time, including me in a year's time.

## The journey of one command

```
python -m csv_insight_lab data.csv --html report.html
```

1. **`__main__.py`** runs when you use `python -m csv_insight_lab`. It only calls `main()` from `cli.py`.
2. **`cli.py` → `main()`** uses `argparse` to turn the words you typed into settings (`args.csv_file`, `args.html`...). `argparse` also produces `--help` for free.
3. **`loader.py` → `load_csv()`** checks the file exists, isn't a folder and isn't empty, then calls `pandas.read_csv()`. If pandas raises one of the errors we expect, it is converted into a `CSVLoadError` with a human message. `main()` catches that, prints it, and returns exit code `1`.
4. **`profiler.py` → `profile_dataframe()`** loops over the columns and calls `profile_column()` for each. The results are stored in two *dataclasses*, `ColumnProfile` and `DatasetProfile`. A dataclass is a class whose job is just to hold named values, so you write `profile.rows` instead of `profile["rows"]`.
5. **`report.py` → `text_report()`** turns the profile into text, and `main()` prints it.
6. If `--html` was given, **`html_report.py`** builds a web page, asking **`charts.py`** for PNG images, and saves it.

The important idea: **steps 3, 4 and 5 don't know about each other's details.** The profiler never prints and the report never calculates. That is why each can be tested on its own.

## Key decisions, in plain words

| Question | Answer in the code | Where |
|---|---|---|
| How do we decide a column is "categorical"? | At most 20 different values, *and* values repeat (different values ≤ half the filled cells) | `classify_column()` |
| Why check boolean before numeric? | pandas also counts True/False as numbers, so the order of the `if`s matters | `classify_column()` |
| How are dates found? | Only the ISO format `2026-10-28`; `03/04/2026` is ambiguous, so it isn't guessed | `parse_iso_dates()` |
| What is a likely ID? | Whole numbers or text where ≥ 95% of values are different | `looks_like_id()` |
| How are duplicates numbered? | `df.duplicated(keep="first")` marks the 2nd, 3rd... copy; row 1 = first row after the header | `profile_dataframe()` |
| Why `utf-8-sig`? | It reads normal UTF-8 *and* removes the invisible marker Excel adds | `load_csv()` |
| Why `html.escape()`? | So text inside a CSV, like `<script>`, is shown, never run | `html_report.py` |

## How the AI-written code was checked

The code was written with an AI assistant, so the useful skill is **checking it**, not typing it:

1. **Run it on real input** and read every line of the output. This found two bugs the tests missed (see the README).
2. **Test the edges:** empty file, header only, missing file, wrong encoding, broken rows. Each has a test in `tests/test_loader.py`.
3. **Check numbers by hand.** `test_numeric_summary_matches_hand_calculation` uses a mean that can be worked out on paper: (10 + 40 + 10 + 10) / 4 = 17.5.
4. **Ask "what would fool this?"** For example: decimal measurements are all different too, so would they be called IDs? (They were about to be; there is now a test.)

## Try these to check your understanding

1. Change `DEFAULT_MAX_CATEGORIES` in `profiler.py` from 20 to 2 and run the tool on the sample file. Which columns change kind, and why?
2. Run `python -m csv_insight_lab examples/sample_canteen_orders.csv --top 1`. What changed?
3. Create a CSV where one row has an extra comma. Run it with and without `--skip-bad-lines`.
4. Write a new test: a column containing only `"yes"` and `"no"` repeated 10 times. What kind should it be? Run `pytest` and see.
