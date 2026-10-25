import io

import pandas as pd

from checker.duplicates import find_duplicates
from checker.missing import find_missing
from checker.report import build_report, remove_duplicates, summarise, to_csv_bytes
from checker.validation import validate

RULES = [
    {"column": "age", "type": "range", "min": 0, "max": 120},
    {"column": "email", "type": "email"},
]


def sample():
    return pd.DataFrame(
        {
            "id": ["1", "2", "2", "3"],
            "age": ["34", "", "", "200"],
            "email": ["a@b.com", "bad", "bad", "c@d.com"],
        }
    )


def run_all(df, rules):
    return find_duplicates(df), find_missing(df), validate(df, rules)


def test_remove_duplicates_keeps_first_and_does_not_mutate():
    df = sample()
    before = df.copy()
    cleaned = remove_duplicates(df)
    assert cleaned["id"].tolist() == ["1", "2", "3"]
    pd.testing.assert_frame_equal(df, before)


def test_summarise_counts():
    df = sample()
    dup, miss, val = run_all(df, RULES)
    s = summarise(df, dup, miss, val)
    assert s["records"] == 4
    assert s["extra_copies"] == 1
    assert s["duplicate_groups"] == 1
    assert s["missing_cells"] == 2
    assert s["validation_failures"] == 3
    assert s["affected_columns"] == ["age", "email"]
    assert s["affected_rows"] == 3  # CSV lines 3, 4 and 5


def test_report_states_cleaning_when_removed():
    df = sample()
    dup, miss, val = run_all(df, RULES)
    text = build_report("test.csv", df, dup, miss, val, ["n/a"], RULES, True)
    assert "Removed 1 exact duplicate" in text
    assert "were not changed" in text


def test_report_no_cleaning_by_default():
    df = sample()
    dup, miss, val = run_all(df, RULES)
    text = build_report("test.csv", df, dup, miss, val, ["n/a"], RULES, False)
    assert "No cleaning applied" in text


def test_csv_round_trip_preserves_values():
    df = sample()
    data = to_csv_bytes(df)
    back = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(df, back)


def test_report_handles_file_with_no_issues():
    df = pd.DataFrame({"id": ["1", "2"]})
    dup, miss, val = run_all(df, [])
    text = build_report("clean.csv", df, dup, miss, val, [], [], False)
    assert "No exact duplicate rows found" in text
    assert "Missing cells: 0" in text