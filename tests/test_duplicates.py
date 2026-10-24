import pandas as pd

from checker.duplicates import find_duplicates


def make_df(rows):
    return pd.DataFrame(rows, columns=["id", "name"])


def test_no_duplicates():
    df = make_df([["1", "A"], ["2", "B"]])
    result = find_duplicates(df)
    assert result["extra_copies"] == 0
    assert result["groups"] == 0
    assert result["details"].empty


def test_one_duplicate_pair():
    df = make_df([["1", "A"], ["2", "B"], ["1", "A"]])
    result = find_duplicates(df)
    assert result["extra_copies"] == 1
    assert result["groups"] == 1
    # rows 1 and 3 of the data = CSV lines 2 and 4
    assert result["details"]["row_number"].tolist() == [2, 4]
    assert result["details"]["is_extra_copy"].tolist() == [False, True]


def test_triplicate_counts_two_extra_copies():
    df = make_df([["1", "A"], ["1", "A"], ["1", "A"], ["2", "B"]])
    result = find_duplicates(df)
    assert result["extra_copies"] == 2
    assert result["groups"] == 1


def test_two_separate_groups():
    df = make_df([["1", "A"], ["2", "B"], ["1", "A"], ["2", "B"]])
    result = find_duplicates(df)
    assert result["extra_copies"] == 2
    assert result["groups"] == 2


def test_near_duplicates_are_not_flagged():
    df = make_df([["1", "Chidi Okafor"], ["1", "Chidi Okafour"]])
    assert find_duplicates(df)["extra_copies"] == 0