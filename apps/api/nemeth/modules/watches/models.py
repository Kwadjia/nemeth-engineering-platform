from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nemeth.core.db import AuditMixin, Base, UUIDPrimaryKeyMixin
from nemeth.modules.products.models import ProductModel

if TYPE_CHECKING:
    from nemeth.modules.prototypes.models import BuildRecord, PartInstance, Prototype


class WatchStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_BUILD = "IN_BUILD"
    BUILT = "BUILT"
    PERSONAL_PROTOTYPE = "PERSONAL_PROTOTYPE"
    DELIVERED = "DELIVERED"
    IN_SERVICE = "IN_SERVICE"
    RETIRED = "RETIRED"


class Watch(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A serialized watch, e.g. N1-001. Its history is the build records, test runs and
    part instances that reference it (ADR-008)."""

    __tablename__ = "watches"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    serial_number: Mapped[str] = mapped_column(String(32), nullable=False)
    product_model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_models.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[WatchStatus] = mapped_column(
        Enum(
            WatchStatus,
            name="watch_status",
            native_enum=False,
            length=24,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=WatchStatus.PLANNED,
        index=True,
    )
    owner_name: Mapped[str | None] = mapped_column(String(200))
    origin_prototype_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("prototypes.id", ondelete="SET NULL")
    )
    assembled_on: Mapped[date | None] = mapped_column(Date)
    delivered_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    product_model: Mapped[ProductModel] = relationship()
    origin_prototype: Mapped[Prototype | None] = relationship(foreign_keys=[origin_prototype_id])
    current_instances: Mapped[list[PartInstance]] = relationship(
        back_populates="current_watch",
        foreign_keys="PartInstance.current_watch_id",
        order_by="PartInstance.identifier",
    )
    build_records: Mapped[list[BuildRecord]] = relationship(
        back_populates="watch",
        foreign_keys="BuildRecord.watch_id",
        order_by="(BuildRecord.performed_on, BuildRecord.created_at)",
    )

    @property
    def installed_count(self) -> int:
        return len(self.current_instances)

    @property
    def build_count(self) -> int:
        return len(self.build_records)

    def __repr__(self) -> str:
        return f"<Watch {self.identifier}>"
