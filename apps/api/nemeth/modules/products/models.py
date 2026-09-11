from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nemeth.core.db import AuditMixin, Base, UUIDPrimaryKeyMixin
from nemeth.core.lifecycle import LifecycleState
from nemeth.modules.components.models import Component


def _lifecycle_column() -> Enum:
    return Enum(
        LifecycleState,
        name="lifecycle_state",
        native_enum=False,
        length=16,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
    )


class Product(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A marketable product line, e.g. NEMETH N1."""

    __tablename__ = "products"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        _lifecycle_column(), nullable=False, default=LifecycleState.CONCEPT
    )
    notes: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    models: Mapped[list[ProductModel]] = relationship(
        back_populates="product", order_by="ProductModel.identifier", cascade="all"
    )

    def __repr__(self) -> str:
        return f"<Product {self.identifier}>"


class Caliber(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A mechanical movement treated as a first-class engineered product."""

    __tablename__ = "calibers"

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        _lifecycle_column(), nullable=False, default=LifecycleState.CONCEPT
    )
    root_component_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("components.id", ondelete="RESTRICT")
    )

    # --- specification (typed where queried; JSONB for the evolving rest) ------------
    architecture: Mapped[str | None] = mapped_column(String(300))
    diameter_mm: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    thickness_mm: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    frequency_bph: Mapped[int | None] = mapped_column(Integer)
    jewel_count: Mapped[int | None] = mapped_column(Integer)
    power_reserve_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    lift_angle_deg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    target_amplitude_deg: Mapped[int | None] = mapped_column(Integer)
    target_rate_tolerance_spd: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    specification: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    notes: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    root_component: Mapped[Component | None] = relationship(foreign_keys=[root_component_id])

    def __repr__(self) -> str:
        return f"<Caliber {self.identifier}>"


class ProductModel(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """A specific configuration (reference) of a product, e.g. N1.01."""

    __tablename__ = "product_models"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        _lifecycle_column(), nullable=False, default=LifecycleState.CONCEPT
    )
    caliber_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("calibers.id", ondelete="RESTRICT")
    )
    root_component_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("components.id", ondelete="RESTRICT")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    product: Mapped[Product] = relationship(back_populates="models")
    caliber: Mapped[Caliber | None] = relationship(foreign_keys=[caliber_id])
    root_component: Mapped[Component | None] = relationship(foreign_keys=[root_component_id])

    def __repr__(self) -> str:
        return f"<ProductModel {self.identifier}>"
