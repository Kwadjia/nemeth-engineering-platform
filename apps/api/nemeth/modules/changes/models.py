from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nemeth.core.db import AuditMixin, Base, UUIDPrimaryKeyMixin
from nemeth.modules.components.models import ComponentRevision
from nemeth.modules.experiments.models import Experiment
from nemeth.modules.testing.models import TestRun


class ChangeStatus(StrEnum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    IMPLEMENTED = "IMPLEMENTED"
    REJECTED = "REJECTED"


class ChangeRole(StrEnum):
    AFFECTED = "AFFECTED"
    PROPOSED = "PROPOSED"


def _enum_column(enum_cls: type[StrEnum], name: str, length: int = 16) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
    )


class EngineeringChange(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """ECR-0021: a recorded decision to move from one revision to another."""

    __tablename__ = "engineering_changes"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ChangeStatus] = mapped_column(
        _enum_column(ChangeStatus, "change_status"),
        nullable=False,
        default=ChangeStatus.DRAFT,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    impact: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(String(120), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    approved_on: Mapped[date | None] = mapped_column(Date)
    implemented_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    revision_links: Mapped[list[ChangeRevision]] = relationship(
        back_populates="change", cascade="all, delete-orphan", order_by="ChangeRevision.created_at"
    )
    experiment_links: Mapped[list[ChangeExperiment]] = relationship(
        back_populates="change",
        cascade="all, delete-orphan",
        order_by="ChangeExperiment.created_at",
    )
    test_run_links: Mapped[list[ChangeTestRun]] = relationship(
        back_populates="change", cascade="all, delete-orphan", order_by="ChangeTestRun.created_at"
    )

    def __repr__(self) -> str:
        return f"<EngineeringChange {self.identifier}>"


class ChangeRevision(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A revision affected by (the 'from') or proposed by (the 'to') a change."""

    __tablename__ = "change_revisions"
    __table_args__ = (UniqueConstraint("change_id", "component_revision_id", "role"),)

    change_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("engineering_changes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("component_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    role: Mapped[ChangeRole] = mapped_column(
        _enum_column(ChangeRole, "change_role"), nullable=False
    )

    change: Mapped[EngineeringChange] = relationship(back_populates="revision_links")
    revision: Mapped[ComponentRevision] = relationship()


class ChangeExperiment(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "change_experiments"
    __table_args__ = (UniqueConstraint("change_id", "experiment_id"),)

    change_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("engineering_changes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("experiments.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    change: Mapped[EngineeringChange] = relationship(back_populates="experiment_links")
    experiment: Mapped[Experiment] = relationship()


class ChangeTestRun(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "change_test_runs"
    __table_args__ = (UniqueConstraint("change_id", "test_run_id"),)

    change_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("engineering_changes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("test_runs.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    change: Mapped[EngineeringChange] = relationship(back_populates="test_run_links")
    test_run: Mapped[TestRun] = relationship()
