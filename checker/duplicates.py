import pandas as pd


def find_duplicates(df: pd.DataFrame) -> dict:
    """Find exact duplicate rows (every column identical).

    The first occurrence is treated as the original; later identical
    rows are "extra copies". Nothing is modified or removed here.
    Row numbers match the line numbers in the CSV file (header = line 1).
    """
    in_group = df.duplicated(keep=False)
    extra_copy = df.duplicated(keep="first")

    details = df[in_group].copy()
    if details.empty:
        return {
            "extra_copies": 0,
            "groups": 0,
            "details": details.assign(
                group_id=pd.Series(dtype=int),
                row_number=pd.Series(dtype=int),
                is_extra_copy=pd.Series(dtype=bool),
            ),
        }

    details["group_id"] = details.groupby(list(df.columns), sort=False).ngroup() + 1
    details["row_number"] = details.index + 2
    details["is_extra_copy"] = extra_copy[in_group]

    return {
        "extra_copies": int(extra_copy.sum()),
        "groups": int(details["group_id"].nunique()),
        "details": details.sort_values(["group_id", "row_number"]),
    }