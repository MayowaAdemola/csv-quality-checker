"""Evaluate the checker against the synthetic dataset's answer key.

Run from the project root:  python scripts/evaluate.py
Writes the measured results to evaluation_results.md.

What is counted:
  duplicates  -> extra copies, identified by CSV line number
  missing     -> missing cells, identified by (CSV line number, column)
  validation  -> failing cells, identified by (CSV line number, column)

Precision = correct detections / everything the tool flagged.
Recall    = correct detections / everything that was injected.
When there is nothing to flag or nothing to find, the score is shown as 1.00.
"""
import platform
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from checker.duplicates import find_duplicates  # noqa: E402
from checker.missing import DEFAULT_MARKERS, find_missing  # noqa: E402
from checker.validation import load_rules, validate  # noqa: E402

DATA_FILE = ROOT / "data" / "synthetic_health_records.csv"
KEY_FILE = ROOT / "data" / "synthetic_health_records_answer_key.csv"
RULES_FILE = ROOT / "rules" / "synthetic_rules.json"
RESULTS_FILE = ROOT / "evaluation_results.md"


def score(expected: set, detected: set) -> dict:
    tp = len(expected & detected)
    fp = len(detected - expected)
    fn = len(expected - detected)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return {
        "expected": len(expected),
        "detected": len(detected),
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall,
        "false_positives": sorted(detected - expected, key=str),
        "false_negatives": sorted(expected - detected, key=str),
    }


def cells(frame: pd.DataFrame) -> set:
    return set(zip(frame["row_number"].astype(int), frame["column"]))


def main():
    df = pd.read_csv(DATA_FILE, dtype=str, keep_default_na=False)
    key = pd.read_csv(KEY_FILE, dtype=str, keep_default_na=False)
    key["row_number"] = key["row_number"].astype(int)
    rules = load_rules(RULES_FILE.read_text(encoding="utf-8"))

    start = time.perf_counter()
    dup = find_duplicates(df)
    miss = find_missing(df, DEFAULT_MARKERS)
    val = validate(df, rules, DEFAULT_MARKERS)
    elapsed = time.perf_counter() - start

    d = dup["details"]
    detected_dup = set(d.loc[d["is_extra_copy"].astype(bool), "row_number"].astype(int))

    expected_dup = set(key.loc[key["issue_type"] == "duplicate", "row_number"])
    expected_missing = cells(key[key["issue_type"] == "missing"])
    expected_invalid = cells(key[key["issue_type"] == "invalid"])

    results = {
        "Duplicate rows (extra copies)": score(expected_dup, detected_dup),
        "Missing cells": score(expected_missing, cells(miss["details"])),
        "Validation failures": score(expected_invalid, cells(val["details"])),
    }

    # Recall for each kind of injected issue
    detected_by_type = {
        "missing": cells(miss["details"]),
        "invalid": cells(val["details"]),
    }
    breakdown = []
    for (issue_type, column, detail), group in key[key["issue_type"] != "duplicate"].groupby(
        ["issue_type", "column", "detail"]
    ):
        group_cells = cells(group)
        found = len(group_cells & detected_by_type[issue_type])
        breakdown.append((issue_type, column, detail, len(group_cells), found))

    lines = []
    add = lines.append
    add("# Evaluation results")
    add("")
    add(f"- Dataset: {DATA_FILE.name} ({len(df):,} records)")
    add(f"- Answer key: {KEY_FILE.name}")
    add(f"- Rules: {RULES_FILE.name}")
    add(f"- Missing-value markers: {', '.join(DEFAULT_MARKERS)}")
    add(f"- Analysis time (duplicates + missing + validation): {elapsed:.3f} seconds")
    add(f"- Environment: Python {platform.python_version()}, pandas {pd.__version__}, "
        f"{platform.system()}")
    add("")
    add("## Detection accuracy")
    add("")
    add("| Check | Injected | Flagged | Correct | False positives | Missed | Precision | Recall |")
    add("|---|---|---|---|---|---|---|---|")
    for name, r in results.items():
        add(f"| {name} | {r['expected']} | {r['detected']} | {r['tp']} | {r['fp']} | "
            f"{r['fn']} | {r['precision']:.2f} | {r['recall']:.2f} |")
    add("")
    add("## Recall by issue type")
    add("")
    add("| Issue | Column | Kind | Injected | Detected |")
    add("|---|---|---|---|---|")
    for issue_type, column, detail, n, found in breakdown:
        add(f"| {issue_type} | {column} | {detail} | {n} | {found} |")
    add("")
    add("## Mismatches")
    add("")
    any_mismatch = False
    for name, r in results.items():
        if r["false_positives"] or r["false_negatives"]:
            any_mismatch = True
            add(f"- {name}: false positives {r['false_positives'][:10]}, "
                f"missed {r['false_negatives'][:10]}")
    if not any_mismatch:
        add("None. Every injected issue was found and nothing else was flagged.")
    add("")
    add("These figures come from one synthetic dataset built to match the rules, "
        "so they show the checker does what it was configured to do. They do not "
        "show how it would perform on real data.")
    add("")

    text = "\n".join(lines)
    RESULTS_FILE.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()