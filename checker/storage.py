import hashlib
import json

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from checker import config
from checker.models import Base, Issue, Run, RuleSet


def make_engine(url: str | None = None):
    url = url or config.database_url()
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite:///") and ":memory:" not in url:
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def init_db(engine) -> None:
    """Create the tables if they do not exist yet."""
    Base.metadata.create_all(engine)


def new_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ----------------------------------------------------------------- rule sets
def save_rule_set(session: Session, name: str, rules: list) -> RuleSet:
    """Save rules as the next version of a named rule set."""
    name = name.strip()
    if not name:
        raise ValueError("A rule set needs a name.")
    latest = session.scalar(select(func.max(RuleSet.version)).where(RuleSet.name == name))
    rule_set = RuleSet(name=name, version=(latest or 0) + 1, rules_json=json.dumps(rules, indent=2))
    session.add(rule_set)
    session.commit()
    return rule_set


def list_rule_sets(session: Session) -> list[RuleSet]:
    return list(session.scalars(select(RuleSet).order_by(RuleSet.name, RuleSet.version.desc())))


def get_rule_set(session: Session, rule_set_id: int) -> RuleSet | None:
    return session.get(RuleSet, rule_set_id)


def rules_of(rule_set: RuleSet) -> list:
    return json.loads(rule_set.rules_json)


# ---------------------------------------------------------------------- runs
def save_run(
    session: Session,
    *,
    filename: str,
    file_bytes: bytes,
    summary: dict,
    markers,
    rule_set_id: int | None,
    duplicates_removed: bool,
    dup: dict,
    missing: dict,
    validation: dict,
    store_values: bool | None = None,
) -> Run:
    """Record one analysis: the summary numbers plus every issue's location.
    The uploaded file itself is never stored, only its SHA-256 fingerprint."""
    if store_values is None:
        store_values = config.store_values()

    run = Run(
        filename=filename,
        file_sha256=sha256_bytes(file_bytes),
        records=summary["records"],
        columns=summary["columns"],
        rule_set_id=rule_set_id,
        markers_json=json.dumps(list(markers)),
        extra_copies=summary["extra_copies"],
        duplicate_groups=summary["duplicate_groups"],
        missing_cells=summary["missing_cells"],
        validation_failures=summary["validation_failures"],
        duplicates_removed=duplicates_removed,
    )

    d = dup["details"]
    for row_number in d.loc[d["is_extra_copy"].astype(bool), "row_number"]:
        run.issues.append(
            Issue(issue_type="duplicate", row_number=int(row_number),
                  column_name="(whole row)", detail="exact copy")
        )
    for r in missing["details"].itertuples(index=False):
        run.issues.append(
            Issue(issue_type="missing", row_number=int(r.row_number), column_name=str(r.column),
                  detail=str(r.reason), value=str(r.value) if store_values else None)
        )
    for r in validation["details"].itertuples(index=False):
        run.issues.append(
            Issue(issue_type="invalid", row_number=int(r.row_number), column_name=str(r.column),
                  detail=str(r.problem), value=str(r.value) if store_values else None)
        )

    session.add(run)
    session.commit()
    return run


def list_runs(session: Session, limit: int = 50) -> list[Run]:
    stmt = select(Run).order_by(Run.created_at.desc(), Run.id.desc()).limit(limit)
    return list(session.scalars(stmt))


def get_run(session: Session, run_id: int) -> Run | None:
    return session.get(Run, run_id)


def issues_for_run(session: Session, run_id: int, issue_type: str | None = None) -> list[Issue]:
    stmt = select(Issue).where(Issue.run_id == run_id).order_by(Issue.row_number, Issue.column_name)
    if issue_type:
        stmt = stmt.where(Issue.issue_type == issue_type)
    return list(session.scalars(stmt))


def delete_run(session: Session, run_id: int) -> bool:
    run = session.get(Run, run_id)
    if run is None:
        return False
    session.delete(run)
    session.commit()
    return True


def attach_artifacts(
    session: Session, run_id: int,
    cleaned_key: str | None = None, report_key: str | None = None,
) -> None:
    """Record where a run's saved files live in the artifact store."""
    run = session.get(Run, run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found.")
    run.cleaned_key = cleaned_key
    run.report_key = report_key
    session.commit()