import pandas as pd
import pytest

from checker.validation import load_rules, validate


def one_col(values):
    return pd.DataFrame({"x": values})


def test_email_rule():
    df = one_col(["a@b.com", "chidi@example", "", "x y@z.com"])
    result = validate(df, [{"column": "x", "type": "email"}])
    assert result["details"]["row_number"].tolist() == [3, 5]  # blank row 4 skipped
    assert result["total_failures"] == 2


def test_date_rule():
    df = one_col(["2026-01-10", "12/01/2026", "2026-02-30"])
    result = validate(df, [{"column": "x", "type": "date", "format": "%Y-%m-%d"}])
    assert result["details"]["row_number"].tolist() == [3, 4]


def test_range_rule():
    df = one_col(["34", "-5", "abc", "121", ""])
    result = validate(df, [{"column": "x", "type": "range", "min": 0, "max": 120}])
    assert result["details"]["row_number"].tolist() == [3, 4, 5]
    assert result["details"]["problem"].tolist() == [
        "outside range",
        "not a number",
        "outside range",
    ]


def test_allowed_rule():
    df = one_col(["M", "F", "X"])
    result = validate(df, [{"column": "x", "type": "allowed", "values": ["M", "F"]}])
    assert result["details"]["row_number"].tolist() == [4]


def test_missing_cells_are_skipped():
    df = one_col(["N/A", "", "2026-01-10"])
    result = validate(df, [{"column": "x", "type": "date"}])
    assert result["total_failures"] == 0
    assert result["summary"].loc[0, "checked"] == 1


def test_unknown_column_is_reported_not_crashed():
    result = validate(one_col(["a"]), [{"column": "nope", "type": "email"}])
    assert result["total_failures"] == 0
    assert len(result["config_errors"]) == 1


def test_unknown_rule_type_is_reported():
    result = validate(one_col(["a"]), [{"column": "x", "type": "magic"}])
    assert len(result["config_errors"]) == 1


def test_nothing_is_modified():
    df = one_col(["a@b.com", "bad"])
    before = df.copy()
    validate(df, [{"column": "x", "type": "email"}])
    pd.testing.assert_frame_equal(df, before)


def test_load_rules_rejects_bad_json():
    with pytest.raises(ValueError):
        load_rules("{not json")


def test_load_rules_rejects_wrong_shape():
    with pytest.raises(ValueError):
        load_rules('{"wrong": []}')