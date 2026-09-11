from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from nemeth.core.db import AuditMixin, Base, UUIDPrimaryKeyMixin


class SupplierKind(StrEnum):
    MACHINE_SHOP = "MACHINE_SHOP"
    MATERIAL = "MATERIAL"
    PLATING = "PLATING"
    HEAT_TREATMENT = "HEAT_TREATMENT"
    COMPONENTS = "COMPONENTS"
    TOOLING = "TOOLING"
    IN_HOUSE = "IN_HOUSE"
    OTHER = "OTHER"


class Supplier(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """An external (or the in-house) source of parts, materials or processes."""

    __tablename__ = "suppliers"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[SupplierKind] = mapped_column(
        Enum(
            SupplierKind,
            name="supplier_kind",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=SupplierKind.OTHER,
        index=True,
    )
    capabilities: Mapped[str | None] = mapped_column(Text)
    contact_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(60))
    website: Mapped[str | None] = mapped_column(String(300))
    address: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<Supplier {self.identifier} {self.name!r}>"
