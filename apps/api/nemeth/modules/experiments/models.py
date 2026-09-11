from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nemeth.core.db import AuditMixin, Base, UUIDPrimaryKeyMixin
from nemeth.modules.components.models import ComponentRevision
from nemeth.modules.prototypes.models import Prototype


class ExperimentStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class ExperimentOutcome(StrEnum):
    IMPROVEMENT = "IMPROVEMENT"
    NO_CHANGE = "NO_CHANGE"
    REGRESSION = "REGRESSION"
    INCONCLUSIVE = "INCONCLUSIVE"


def _enum_column(enum_cls: type[StrEnum], name: str, length: int = 16) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
    )


class Experiment(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A hypothesis-driven piece of development work, e.g. EXP-014."""

    __tablename__ = "experiments"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(
        _enum_column(ExperimentStatus, "experiment_status"),
        nullable=False,
        default=ExperimentStatus.PLANNED,
        index=True,
    )
    outcome: Mapped[ExperimentOutcome | None] = mapped_column(
        _enum_column(ExperimentOutcome, "experiment_outcome")
    )
    objective: Mapped[str | None] = mapped_column(Text)
    hypothesis: Mapped[str | None] = mapped_column(Text)
    configuration: Mapped[str | None] = mapped_column(Text)
    methodology: Mapped[str | None] = mapped_column(Text)
    equipment: Mapped[str | None] = mapped_column(Text)
    procedure: Mapped[str | None] = mapped_column(Text)
    observations: Mapped[str | None] = mapped_column(Text)
    results: Mapped[str | None] = mapped_column(Text)
    conclusion: Mapped[str | None] = mapped_column(Text)
    follow_up: Mapped[str | None] = mapped_column(Text)
    started_on: Mapped[date | None] = mapped_column(Date)
    completed_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    prototype_links: Mapped[list[ExperimentPrototype]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="ExperimentPrototype.created_at",
    )
    revision_links: Mapped[list[ExperimentRevision]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="ExperimentRevision.created_at",
    )

    def __repr__(self) -> str:
        return f"<Experiment {self.identifier}>"


class ExperimentPrototype(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A prototype involved in an experiment (subject, control, …)."""

    __tablename__ = "experiment_prototypes"
    __table_args__ = (UniqueConstraint("experiment_id", "prototype_id"),)

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prototype_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("prototypes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    role: Mapped[str | None] = mapped_column(String(80))

    experiment: Mapped[Experiment] = relationship(back_populates="prototype_links")
    prototype: Mapped[Prototype] = relationship()


class ExperimentRevision(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A component revision involved in an experiment (before, after, under test, …)."""

    __tablename__ = "experiment_revisions"
    __table_args__ = (UniqueConstraint("experiment_id", "component_revision_id"),)

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("component_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    role: Mapped[str | None] = mapped_column(String(80))

    experiment: Mapped[Experiment] = relationship(back_populates="revision_links")
    revision: Mapped[ComponentRevision] = relationship()
