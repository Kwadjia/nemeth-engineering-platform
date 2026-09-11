from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
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
from nemeth.core.lifecycle import ALLOWED_TRANSITIONS, LifecycleState, is_frozen

if TYPE_CHECKING:
    from nemeth.modules.bom.models import BomLine
    from nemeth.modules.suppliers.models import Supplier


class ComponentKind(StrEnum):
    PART = "PART"
    ASSEMBLY = "ASSEMBLY"


class ComponentFamily(StrEnum):
    WATCH = "WATCH"
    CASE = "CASE"
    DIAL = "DIAL"
    HAND = "HAND"
    MVT = "MVT"
    STRAP = "STRAP"
    PKG = "PKG"
    MISC = "MISC"


def _enum_column(enum_cls: type[StrEnum], name: str, length: int = 16) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
    )


class Component(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """The identity of an engineered item. Engineering content lives on revisions."""

    __tablename__ = "components"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[ComponentKind] = mapped_column(
        _enum_column(ComponentKind, "component_kind"), nullable=False
    )
    family: Mapped[ComponentFamily] = mapped_column(
        _enum_column(ComponentFamily, "component_family"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    revisions: Mapped[list[ComponentRevision]] = relationship(
        back_populates="component",
        order_by="ComponentRevision.revision_number",
        cascade="all",
        foreign_keys="ComponentRevision.component_id",
    )

    @property
    def latest_revision(self) -> ComponentRevision | None:
        return self.revisions[-1] if self.revisions else None

    @property
    def released_revision(self) -> ComponentRevision | None:
        for rev in reversed(self.revisions):
            if rev.lifecycle_state == LifecycleState.RELEASED:
                return rev
        return None

    @property
    def revision_count(self) -> int:
        return len(self.revisions)

    def __repr__(self) -> str:
        return f"<Component {self.identifier} {self.name!r}>"


class ComponentRevision(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """Engineering content of a component at a point in time. Frozen from PROTOTYPE on."""

    __tablename__ = "component_revisions"
    __table_args__ = (
        UniqueConstraint("component_id", "revision_number"),
        UniqueConstraint("component_id", "revision_label"),
    )

    component_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("components.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_label: Mapped[str] = mapped_column(String(8), nullable=False)
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        _enum_column(LifecycleState, "lifecycle_state"),
        nullable=False,
        default=LifecycleState.CONCEPT,
        index=True,
    )
    change_summary: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    # --- engineering content (copied forward when a new revision is created) --------
    material: Mapped[str | None] = mapped_column(String(200))
    heat_treatment: Mapped[str | None] = mapped_column(String(200))
    finish: Mapped[str | None] = mapped_column(String(200))
    manufacturing_method: Mapped[str | None] = mapped_column(String(200))
    dimensions: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tolerances: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    mass_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    supplier_note: Mapped[str | None] = mapped_column(String(300))
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    inspection_requirements: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    # --- history ------------------------------------------------------------------
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("component_revisions.id", ondelete="SET NULL", use_alter=True)
    )

    component: Mapped[Component] = relationship(
        back_populates="revisions", foreign_keys=[component_id]
    )
    supplier: Mapped[Supplier | None] = relationship(foreign_keys=[supplier_id])
    superseded_by: Mapped[ComponentRevision | None] = relationship(
        remote_side="ComponentRevision.id", foreign_keys=[superseded_by_id]
    )
    bom_lines: Mapped[list[BomLine]] = relationship(
        back_populates="parent_revision",
        foreign_keys="BomLine.parent_revision_id",
        order_by="BomLine.find_number",
        cascade="all, delete-orphan",
    )

    #: Fields that constitute copyable engineering content.
    CONTENT_FIELDS: tuple[str, ...] = (
        "description",
        "material",
        "heat_treatment",
        "finish",
        "manufacturing_method",
        "dimensions",
        "tolerances",
        "mass_g",
        "supplier_note",
        "supplier_id",
        "inspection_requirements",
        "notes",
    )

    @property
    def is_frozen(self) -> bool:
        return is_frozen(self.lifecycle_state)

    @property
    def display_identifier(self) -> str:
        return f"{self.component.identifier} Rev {self.revision_label}"

    @property
    def allowed_transitions(self) -> list[LifecycleState]:
        return sorted(ALLOWED_TRANSITIONS[self.lifecycle_state], key=lambda s: s.value)

    def __repr__(self) -> str:
        return f"<ComponentRevision {self.component_id} Rev {self.revision_label}>"
