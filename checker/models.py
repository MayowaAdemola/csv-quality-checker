from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RuleSet(Base):
    """A named, versioned set of validation rules. Saving never overwrites:
    each save is a new version, so old runs always point at the exact rules used."""

    __tablename__ = "rule_sets"
    __table_args__ = (UniqueConstraint("name", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer)
    rules_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Run(Base):
    """One analysis of one uploaded file."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    filename: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    records: Mapped[int] = mapped_column(Integer)
    columns: Mapped[int] = mapped_column(Integer)
    rule_set_id: Mapped[int | None] = mapped_column(ForeignKey("rule_sets.id"), nullable=True)
    markers_json: Mapped[str] = mapped_column(Text, default="[]")
    extra_copies: Mapped[int] = mapped_column(Integer)
    duplicate_groups: Mapped[int] = mapped_column(Integer)
    missing_cells: Mapped[int] = mapped_column(Integer)
    validation_failures: Mapped[int] = mapped_column(Integer)
    duplicates_removed: Mapped[bool] = mapped_column(Boolean, default=False)
    cleaned_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    report_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    issues: Mapped[list["Issue"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Issue(Base):
    """One detected problem: where it is and what it is. The cell value is
    only stored when STORE_VALUES is enabled."""

    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    issue_type: Mapped[str] = mapped_column(String(20))  # duplicate | missing | invalid
    row_number: Mapped[int] = mapped_column(Integer)
    column_name: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(String(255))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["Run"] = relationship(back_populates="issues")