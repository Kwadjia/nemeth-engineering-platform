from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from nemeth.core.lifecycle import LifecycleState
from nemeth.modules.components.schemas import AuditFields, ComponentSummary

# --- products ----------------------------------------------------------------------


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    name: str
    lifecycle_state: LifecycleState
    is_placeholder: bool


class ProductModelSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    name: str
    lifecycle_state: LifecycleState
    is_placeholder: bool


class ProductCreate(BaseModel):
    identifier: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    lifecycle_state: LifecycleState = LifecycleState.CONCEPT
    notes: str | None = None
    is_placeholder: bool = False


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    lifecycle_state: LifecycleState | None = None
    notes: str | None = None
    is_placeholder: bool | None = None


class ProductRead(ProductSummary, AuditFields):
    description: str | None
    notes: str | None
    models: list[ProductModelSummary]


# --- calibers ----------------------------------------------------------------------


class CaliberSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    name: str
    lifecycle_state: LifecycleState
    is_placeholder: bool


class CaliberSpecification(BaseModel):
    architecture: str | None = Field(default=None, max_length=300)
    diameter_mm: Decimal | None = Field(default=None, gt=0)
    thickness_mm: Decimal | None = Field(default=None, gt=0)
    frequency_bph: int | None = Field(default=None, gt=0)
    jewel_count: int | None = Field(default=None, ge=0)
    power_reserve_hours: Decimal | None = Field(default=None, gt=0)
    lift_angle_deg: Decimal | None = Field(default=None, gt=0, lt=90)
    target_amplitude_deg: int | None = Field(default=None, gt=0, lt=360)
    target_rate_tolerance_spd: Decimal | None = Field(default=None, ge=0)
    specification: dict[str, Any] | None = Field(
        default=None,
        description="Evolving fields: barrel configuration, gear ratios, tooth counts, balance inertia, hairspring, escapement geometry.",
    )


class CaliberCreate(CaliberSpecification):
    identifier: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    lifecycle_state: LifecycleState = LifecycleState.CONCEPT
    root_component_id: uuid.UUID | None = None
    notes: str | None = None
    is_placeholder: bool = False


class CaliberUpdate(CaliberSpecification):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    lifecycle_state: LifecycleState | None = None
    root_component_id: uuid.UUID | None = None
    notes: str | None = None
    is_placeholder: bool | None = None


class CaliberRead(CaliberSummary, CaliberSpecification, AuditFields):
    description: str | None
    notes: str | None
    root_component: ComponentSummary | None


# --- product models (references) ---------------------------------------------------


class ProductModelCreate(BaseModel):
    identifier: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    lifecycle_state: LifecycleState = LifecycleState.CONCEPT
    caliber_id: uuid.UUID | None = None
    root_component_id: uuid.UUID | None = None
    notes: str | None = None
    is_placeholder: bool = False


class ProductModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    lifecycle_state: LifecycleState | None = None
    caliber_id: uuid.UUID | None = None
    root_component_id: uuid.UUID | None = None
    notes: str | None = None
    is_placeholder: bool | None = None


class ProductModelRead(ProductModelSummary, AuditFields):
    description: str | None
    notes: str | None
    product: ProductSummary
    caliber: CaliberSummary | None
    root_component: ComponentSummary | None
