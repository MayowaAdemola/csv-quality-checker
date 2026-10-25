import io

import pandas as pd
import pytest

from checker.duplicates import find_duplicates
from checker.missing import find_missing
from checker.validation import validate


def header_only():
    return pd.DataFrame({"id": pd.Series([], dtype=str), "age": pd.Series([], dtype=str)})


def test_header_only_file_does_not_crash():
    df = header_only()
    assert find_duplicates(df)["extra_copies"] == 0
    assert find_missing(df)["total_missing"] == 0
    rules = [{"column": "age", "type": "range", "min": 0, "max": 120}]
    assert validate(df, rules)["total_failures"] == 0


def test_empty_file_raises_empty_data_error():
    with pytest.raises(pd.errors.EmptyDataError):
        pd.read_csv(io.StringIO(""), dtype=str, keep_default_na=False)


def test_ragged_csv_does_not_crash_the_checks():
    # Row 2 has fewer fields, row 3 has more fields than the header.
    text = "id,age\n1,34\n2\n3,40,extra\n"
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except pd.errors.ParserError:
        return  # the app shows "Could not read this file as a CSV"
    find_duplicates(df)
    find_missing(df)


def test_unexpected_values_are_reported_not_crashed():
    df = pd.DataFrame({"age": ["34", "abc", "1e9", "3 4", "NaN"]})
    rules = [{"column": "age", "type": "range", "min": 0, "max": 120}]
    result = validate(df, rules)
    flagged = set(result["details"]["value"])
    assert flagged == {"abc", "1e9", "3 4"}
    # "NaN" is a default missing marker, so it is skipped here
    assert "NaN" not in flagged


def test_column_with_only_missing_values():
    df = pd.DataFrame({"age": ["", "N/A", "  "]})
    assert find_missing(df)["total_missing"] == 3
    rules = [{"column": "age", "type": "range", "min": 0, "max": 120}]
    result = validate(df, rules)
    assert result["total_failures"] == 0
    assert result["summary"].loc[0, "checked"] == 0