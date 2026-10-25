import json
from datetime import datetime

import pandas as pd


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy without exact duplicate rows (first occurrence kept)."""
    return df[~df.duplicated(keep="first")].reset_index(drop=True)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialise to CSV exactly as read: blanks stay blank, nothing is reformatted."""
    return df.to_csv(index=False).encode("utf-8")


def summarise(df, dup, missing, validation) -> dict:
    """Headline numbers. 'Affected rows' = rows with at least one missing cell,
    validation failure, or that are an extra copy of an earlier row."""
    dup_details = dup["details"]
    extra_rows = dup_details[dup_details["is_extra_copy"].astype(bool)]["row_number"]

    columns = set(missing["details"]["column"]) | set(validation["details"]["column"])
    rows = (
        set(missing["details"]["row_number"])
        | set(validation["details"]["row_number"])
        | set(extra_rows)
    )
    return {
        "records": len(df),
        "columns": len(df.columns),
        "extra_copies": dup["extra_copies"],
        "duplicate_groups": dup["groups"],
        "missing_cells": missing["total_missing"],
        "validation_failures": validation["total_failures"],
        "affected_columns": sorted(columns),
        "affected_rows": len(rows),
    }


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_None._"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "|" + "|".join("---" for _ in cols) + "|",
    ]
    for row in df.itertuples(index=False):
        cells = [str(v).replace("|", "\\|").replace("\n", " ") for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _limited(df: pd.DataFrame, max_rows: int) -> str:
    note = ""
    if len(df) > max_rows:
        note = f"\n\n_Showing the first {max_rows} of {len(df)} rows._"
        df = df.head(max_rows)
    return _md_table(df) + note


def build_report(
    filename, df, dup, missing, validation, markers, rules,
    removed_duplicates: bool, max_rows: int = 500,
) -> str:
    s = summarise(df, dup, missing, validation)
    out = []
    add = out.append

    add("# Data-quality report")
    add("")
    add(f"- File: {filename}")
    add(f"- Generated: {datetime.now():%Y-%m-%d %H:%M}")
    add("- Row numbers match CSV line numbers (the header is line 1).")
    add("")
    add("## Summary")
    add("")
    add(f"- Records analysed: {s['records']}")
    add(f"- Columns: {s['columns']}")
    add(f"- Extra duplicate rows: {s['extra_copies']} (in {s['duplicate_groups']} group(s))")
    add(f"- Missing cells: {s['missing_cells']}")
    add(f"- Validation failures: {s['validation_failures']}")
    add(f"- Rows with at least one issue: {s['affected_rows']}")
    add(f"- Columns with missing values or validation failures: "
        f"{', '.join(s['affected_columns']) or 'none'}")
    add("")

    add("## Exact duplicate rows")
    add("")
    if s["extra_copies"] == 0:
        add("No exact duplicate rows found.")
    else:
        cols = ["group_id", "row_number", "is_extra_copy"]
        add(_limited(dup["details"][cols], max_rows))
    add("")

    add("## Missing values")
    add("")
    add("Blank and whitespace-only cells are always counted. "
        f"Values also treated as missing: {', '.join(markers) or 'none'}.")
    add("")
    summary = missing["summary"]
    add(_md_table(summary[summary["missing"] > 0]))
    add("")
    if s["missing_cells"] > 0:
        add("### Every missing cell")
        add("")
        add(_limited(missing["details"], max_rows))
        add("")

    add("## Validation")
    add("")
    add("Rules applied:")
    add("")
    add("```json")
    add(json.dumps(rules, indent=2))
    add("```")
    add("")
    for msg in validation["config_errors"]:
        add(f"- Warning: {msg}")
    if validation["config_errors"]:
        add("")
    add(_md_table(validation["summary"]))
    add("")
    if s["validation_failures"] > 0:
        add("### Every failing cell")
        add("")
        add(_limited(validation["details"], max_rows))
        add("")

    add("## Cleaning actions")
    add("")
    if removed_duplicates and s["extra_copies"] > 0:
        d = dup["details"]
        lines = d[d["is_extra_copy"].astype(bool)]["row_number"].tolist()
        add(f"- Removed {s['extra_copies']} exact duplicate row(s), keeping the first "
            f"occurrence of each. Removed CSV lines: {', '.join(map(str, lines))}.")
    elif removed_duplicates:
        add("- Duplicate removal was selected, but no exact duplicates were found.")
    else:
        add("- No cleaning applied. The cleaned file is identical to the original.")
    add("- Missing values and invalid entries were not changed.")
    add("")
    return "\n".join(out)