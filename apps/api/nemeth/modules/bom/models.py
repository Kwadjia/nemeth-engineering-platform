from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nemeth.core.db import AuditMixin, Base, UUIDPrimaryKeyMixin
from nemeth.modules.components.models import Component, ComponentRevision


class BomLine(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """One line on the design BOM of an assembly revision (ADR-006)."""

    __tablename__ = "bom_lines"
    __table_args__ = (
        UniqueConstraint("parent_revision_id", "find_number"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )

    parent_revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("component_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_component_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("components.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    child_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("component_revisions.id", ondelete="RESTRICT"), index=True
    )
    find_number: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal(1))
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="ea")
    reference_designator: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    parent_revision: Mapped[ComponentRevision] = relationship(
        back_populates="bom_lines", foreign_keys=[parent_revision_id]
    )
    child_component: Mapped[Component] = relationship(foreign_keys=[child_component_id])
    child_revision: Mapped[ComponentRevision | None] = relationship(
        foreign_keys=[child_revision_id]
    )

    @property
    def is_pinned(self) -> bool:
        return self.child_revision_id is not None

    def __repr__(self) -> str:
        return f"<BomLine {self.find_number} -> {self.child_component_id} x{self.quantity}>"
