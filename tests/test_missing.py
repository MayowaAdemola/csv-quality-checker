import pandas as pd

from checker.missing import find_missing


def make_df():
    return pd.DataFrame(
        {
            "id": ["1", "2", "3", "4"],
            "age": ["34", "", "N/A", "  "],
        }
    )


def test_counts_blank_whitespace_and_marker():
    result = find_missing(make_df())
    age = result["summary"].set_index("column").loc["age"]
    assert age["blank"] == 2      # "" and "  "
    assert age["marker"] == 1     # "N/A"
    assert age["missing"] == 3
    assert age["missing_pct"] == 75.0
    assert result["total_missing"] == 3


def test_complete_column_has_no_missing():
    result = find_missing(make_df())
    ident = result["summary"].set_index("column").loc["id"]
    assert ident["missing"] == 0


def test_markers_are_case_insensitive():
    df = pd.DataFrame({"x": ["NULL", "Null", "null", "ok"]})
    assert find_missing(df)["total_missing"] == 3


def test_custom_markers_replace_defaults():
    df = pd.DataFrame({"x": ["N/A", "unknown", "ok"]})
    result = find_missing(df, markers=["unknown"])
    assert result["total_missing"] == 1
    assert result["details"].loc[0, "value"] == "unknown"


def test_row_numbers_match_csv_lines():
    result = find_missing(make_df())
    # data rows 1 and 2 (0-based) are CSV lines 3 and 4 (and 5 for "  ")
    assert result["details"]["row_number"].tolist() == [3, 4, 5]


def test_nothing_is_modified():
    df = make_df()
    before = df.copy()
    find_missing(df)
    pd.testing.assert_frame_equal(df, before)