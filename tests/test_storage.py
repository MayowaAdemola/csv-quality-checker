import hashlib

import pandas as pd
import pytest

from checker.duplicates import find_duplicates
from checker.missing import DEFAULT_MARKERS, find_missing
from checker.report import summarise
from checker.storage import (
    delete_run, get_run, init_db, issues_for_run, list_rule_sets, list_runs,
    make_engine, new_session_factory, rules_of, save_rule_set, save_run,
)
from checker.validation import validate

RULES = [
    {"column": "age", "type": "range", "min": 0, "max": 120},
    {"column": "email", "type": "email"},
]
FILE_BYTES = b"id,age,email\n1,34,a@b.com\n"


@pytest.fixture
def session():
    engine = make_engine("sqlite://")  # in-memory database, gone after each test
    init_db(engine)
    with new_session_factory(engine)() as s:
        yield s


def sample_df():
    return pd.DataFrame(
        {
            "id": ["1", "2", "2", "3"],
            "age": ["34", "", "", "200"],
            "email": ["a@b.com", "bad", "bad", "c@d.com"],
        }
    )


def make_run(session, store_values=False, rule_set_id=None, file_bytes=FILE_BYTES):
    df = sample_df()
    dup = find_duplicates(df)
    miss = find_missing(df, DEFAULT_MARKERS)
    val = validate(df, RULES, DEFAULT_MARKERS)
    return save_run(
        session, filename="sample.csv", file_bytes=file_bytes,
        summary=summarise(df, dup, miss, val), markers=DEFAULT_MARKERS,
        rule_set_id=rule_set_id, duplicates_removed=False,
        dup=dup, missing=miss, validation=val, store_values=store_values,
    )


def test_rule_set_versions_increment(session):
    first = save_rule_set(session, "health", RULES)
    second = save_rule_set(session, "health", RULES[:1])
    other = save_rule_set(session, "other", RULES)
    assert (first.version, second.version, other.version) == (1, 2, 1)
    names = [(r.name, r.version) for r in list_rule_sets(session)]
    assert names == [("health", 2), ("health", 1), ("other", 1)]


def test_rule_set_requires_a_name(session):
    with pytest.raises(ValueError):
        save_rule_set(session, "   ", RULES)


def test_rules_round_trip(session):
    rule_set = save_rule_set(session, "health", RULES)
    assert rules_of(rule_set) == RULES


def test_save_run_stores_summary_and_fingerprint(session):
    run = make_run(session)
    assert run.records == 4
    assert run.extra_copies == 1
    assert run.duplicate_groups == 1
    assert run.missing_cells == 2
    assert run.validation_failures == 3
    assert run.file_sha256 == hashlib.sha256(FILE_BYTES).hexdigest()


def test_save_run_stores_every_issue(session):
    run = make_run(session)
    issues = issues_for_run(session, run.id)
    assert len(issues) == 6
    kinds = sorted(i.issue_type for i in issues)
    assert kinds == ["duplicate", "invalid", "invalid", "invalid", "missing", "missing"]
    duplicate = issues_for_run(session, run.id, "duplicate")[0]
    assert duplicate.row_number == 4  # CSV line of the extra copy


def test_values_are_not_stored_by_default(session):
    run = make_run(session)
    assert all(i.value is None for i in issues_for_run(session, run.id))


def test_values_are_stored_when_enabled(session):
    run = make_run(session, store_values=True)
    invalid_values = {i.value for i in issues_for_run(session, run.id, "invalid")}
    assert invalid_values == {"bad", "200"}


def test_runs_are_listed_newest_first(session):
    first = make_run(session)
    second = make_run(session)
    assert [r.id for r in list_runs(session)] == [second.id, first.id]


def test_run_links_to_the_rule_set_used(session):
    rule_set = save_rule_set(session, "health", RULES)
    run = make_run(session, rule_set_id=rule_set.id)
    assert get_run(session, run.id).rule_set_id == rule_set.id


def test_delete_run_removes_its_issues(session):
    run = make_run(session)
    assert delete_run(session, run.id) is True
    assert get_run(session, run.id) is None
    assert issues_for_run(session, run.id) == []
    assert delete_run(session, run.id) is False


def test_same_file_gives_same_fingerprint(session):
    a = make_run(session)
    b = make_run(session)
    assert a.file_sha256 == b.file_sha256