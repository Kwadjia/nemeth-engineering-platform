from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nemeth.core.db import AuditMixin, Base, UUIDPrimaryKeyMixin
from nemeth.modules.components.models import Component, ComponentRevision
from nemeth.modules.products.models import Caliber, ProductModel


class PrototypeStatus(StrEnum):
    PLANNED = "PLANNED"
    BUILDING = "BUILDING"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class PartSource(StrEnum):
    IN_HOUSE = "IN_HOUSE"
    PURCHASED = "PURCHASED"
    SALVAGED = "SALVAGED"
    OTHER = "OTHER"


class PartInstanceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    INSTALLED = "INSTALLED"
    REMOVED = "REMOVED"
    SCRAPPED = "SCRAPPED"


class BuildAction(StrEnum):
    INSTALL = "INSTALL"
    REMOVE = "REMOVE"


def _enum_column(enum_cls: type[StrEnum], name: str, length: int = 16) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
    )


class Prototype(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A physical development build, e.g. N1-P001."""

    __tablename__ = "prototypes"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PrototypeStatus] = mapped_column(
        _enum_column(PrototypeStatus, "prototype_status"),
        nullable=False,
        default=PrototypeStatus.PLANNED,
        index=True,
    )
    product_model_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("product_models.id", ondelete="RESTRICT")
    )
    caliber_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("calibers.id", ondelete="RESTRICT")
    )
    started_on: Mapped[date | None] = mapped_column(Date)
    retired_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    product_model: Mapped[ProductModel | None] = relationship(foreign_keys=[product_model_id])
    caliber: Mapped[Caliber | None] = relationship(foreign_keys=[caliber_id])
    current_instances: Mapped[list[PartInstance]] = relationship(
        back_populates="current_prototype",
        foreign_keys="PartInstance.current_prototype_id",
        order_by="PartInstance.identifier",
    )
    build_records: Mapped[list[BuildRecord]] = relationship(
        back_populates="prototype",
        order_by="(BuildRecord.performed_on, BuildRecord.created_at)",
        cascade="all",
    )

    @property
    def installed_count(self) -> int:
        return len(self.current_instances)

    @property
    def build_count(self) -> int:
        return len(self.build_records)

    def __repr__(self) -> str:
        return f"<Prototype {self.identifier}>"


class PartInstance(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """One physical part, made or bought to an exact frozen revision."""

    __tablename__ = "part_instances"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    component_revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("component_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    serial_number: Mapped[str | None] = mapped_column(String(120))
    lot: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[PartSource] = mapped_column(
        _enum_column(PartSource, "part_source"), nullable=False, default=PartSource.IN_HOUSE
    )
    status: Mapped[PartInstanceStatus] = mapped_column(
        _enum_column(PartInstanceStatus, "part_instance_status"),
        nullable=False,
        default=PartInstanceStatus.AVAILABLE,
        index=True,
    )
    material_lot: Mapped[str | None] = mapped_column(String(120))
    heat_treatment_lot: Mapped[str | None] = mapped_column(String(120))
    supplier_note: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_prototype_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("prototypes.id", ondelete="SET NULL"), index=True
    )

    revision: Mapped[ComponentRevision] = relationship(foreign_keys=[component_revision_id])
    current_prototype: Mapped[Prototype | None] = relationship(
        back_populates="current_instances", foreign_keys=[current_prototype_id]
    )

    @property
    def component(self) -> Component:
        return self.revision.component

    def __repr__(self) -> str:
        return f"<PartInstance {self.identifier}>"


class BuildRecord(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """An append-only assembly event on a prototype (watches join in slice 10)."""

    __tablename__ = "build_records"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    prototype_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("prototypes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    performed_on: Mapped[date] = mapped_column(Date, nullable=False)
    performed_by: Mapped[str] = mapped_column(String(120), nullable=False)
    procedure: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    prototype: Mapped[Prototype] = relationship(back_populates="build_records")
    entries: Mapped[list[BuildEntry]] = relationship(
        back_populates="build_record",
        order_by="BuildEntry.sequence",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BuildRecord {self.identifier}>"


class BuildEntry(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """One install or removal of a part instance within a build record."""

    __tablename__ = "build_entries"
    __table_args__ = (
        UniqueConstraint("build_record_id", "sequence"),
        UniqueConstraint("build_record_id", "part_instance_id"),
    )

    build_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("build_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    part_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("part_instances.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[BuildAction] = mapped_column(
        _enum_column(BuildAction, "build_action"), nullable=False
    )
    position: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    build_record: Mapped[BuildRecord] = relationship(back_populates="entries")
    part_instance: Mapped[PartInstance] = relationship(foreign_keys=[part_instance_id])

    @property
    def revision(self) -> ComponentRevision:
        return self.part_instance.revision

    @property
    def component(self) -> Component:
        return self.part_instance.revision.component

    def __repr__(self) -> str:
        return f"<BuildEntry {self.sequence} {self.action.value} {self.part_instance_id}>"
