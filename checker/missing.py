import pandas as pd

DEFAULT_MARKERS = ["n/a", "na", "null", "none", "nan", "-", "--"]


def find_missing(df: pd.DataFrame, markers=None) -> dict:
    """Find missing values without modifying the data.

    A cell counts as missing if it is blank/whitespace-only, or if its
    trimmed, lower-cased text matches one of the markers.
    Row numbers match CSV line numbers (header = line 1).
    """
    if markers is None:
        markers = DEFAULT_MARKERS
    marker_set = {m.strip().lower() for m in markers if m.strip()}

    stripped = df.apply(lambda col: col.str.strip())
    is_blank = stripped == ""
    is_marker = stripped.apply(lambda col: col.str.lower().isin(marker_set)) & ~is_blank

    n_rows = len(df)
    blank_counts = is_blank.sum()
    marker_counts = is_marker.sum()
    missing_counts = blank_counts + marker_counts

    summary = pd.DataFrame(
        {
            "column": df.columns,
            "blank": blank_counts.values,
            "marker": marker_counts.values,
            "missing": missing_counts.values,
            "missing_pct": (
                (missing_counts / n_rows * 100).round(1).values if n_rows else 0.0
            ),
        }
    )

    rows = []
    for col in df.columns:
        for idx in df.index[is_blank[col] | is_marker[col]]:
            rows.append(
                {
                    "row_number": idx + 2,
                    "column": col,
                    "value": df.at[idx, col],
                    "reason": "blank" if is_blank.at[idx, col] else "marker",
                }
            )
    details = pd.DataFrame(rows, columns=["row_number", "column", "value", "reason"])
    details = details.sort_values(["row_number", "column"]).reset_index(drop=True)

    return {
        "total_missing": int(missing_counts.sum()),
        "summary": summary,
        "details": details,
    }