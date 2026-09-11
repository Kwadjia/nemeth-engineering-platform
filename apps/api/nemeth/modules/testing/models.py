from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nemeth.core.db import AuditMixin, Base, UUIDPrimaryKeyMixin
from nemeth.modules.components.models import ComponentRevision
from nemeth.modules.experiments.models import Experiment
from nemeth.modules.prototypes.models import PartInstance, Prototype


class TestOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INFO = "INFO"


#: Timegrapher positions: dial up/down, crown up/down/left/right.
POSITIONS: tuple[str, ...] = ("DU", "DD", "CU", "CD", "CL", "CR")
POSITION_LABELS: dict[str, str] = {
    "DU": "Dial up",
    "DD": "Dial down",
    "CU": "Crown up",
    "CD": "Crown down",
    "CL": "Crown left",
    "CR": "Crown right",
}


def _enum_column(enum_cls: type[StrEnum], name: str, length: int = 16) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
    )


class TestType(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A registry row describing what a kind of test measures. New tests are rows."""

    __tablename__ = "test_types"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    #: [{"key": "rate_sec_day", "label": "Rate", "unit": "s/d"}, …]
    metrics: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    allow_custom_metrics: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uses_positions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def metric_units(self) -> dict[str, str | None]:
        return {m["key"]: m.get("unit") for m in self.metrics}

    def __repr__(self) -> str:
        return f"<TestType {self.code}>"


class TestRun(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """One testing session against at most one subject, optionally within an experiment."""

    __tablename__ = "test_runs"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN prototype_id IS NULL THEN 0 ELSE 1 END)"
            " + (CASE WHEN part_instance_id IS NULL THEN 0 ELSE 1 END)"
            " + (CASE WHEN component_revision_id IS NULL THEN 0 ELSE 1 END) <= 1",
            name="single_subject",
        ),
    )

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    test_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("test_types.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(200))
    prototype_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("prototypes.id", ondelete="RESTRICT"), index=True
    )
    part_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("part_instances.id", ondelete="RESTRICT"), index=True
    )
    component_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("component_revisions.id", ondelete="RESTRICT"), index=True
    )
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("experiments.id", ondelete="RESTRICT"), index=True
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    performed_by: Mapped[str] = mapped_column(String(120), nullable=False)
    equipment: Mapped[str | None] = mapped_column(String(200))
    #: {"temperature_c": 22.5, "humidity_pct": 40, "state_of_wind": "full"}
    conditions: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    outcome: Mapped[TestOutcome] = mapped_column(
        _enum_column(TestOutcome, "test_outcome", length=8),
        nullable=False,
        default=TestOutcome.INFO,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    test_type: Mapped[TestType] = relationship()
    prototype: Mapped[Prototype | None] = relationship()
    part_instance: Mapped[PartInstance | None] = relationship()
    revision: Mapped[ComponentRevision | None] = relationship()
    experiment: Mapped[Experiment | None] = relationship()
    measurements: Mapped[list[Measurement]] = relationship(
        back_populates="test_run", order_by="Measurement.sequence", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestRun {self.identifier}>"


class Measurement(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """One observation: a metric, a value, optionally a position. Long format on purpose."""

    __tablename__ = "measurements"
    __table_args__ = (UniqueConstraint("test_run_id", "sequence"),)

    test_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(16))
    position: Mapped[str | None] = mapped_column(String(8), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    test_run: Mapped[TestRun] = relationship(back_populates="measurements")

    def __repr__(self) -> str:
        return f"<Measurement {self.metric}={self.value} {self.position or ''}>"
