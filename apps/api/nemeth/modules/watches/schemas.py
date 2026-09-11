from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nemeth.modules.components.schemas import AuditFields
from nemeth.modules.products.schemas import ProductModelSummary
from nemeth.modules.watches.models import WatchStatus


class WatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    serial_number: str
    status: WatchStatus
    owner_name: str | None
    is_placeholder: bool


class WatchRead(WatchSummary, AuditFields):
    product_model: ProductModelSummary
    origin_prototype_identifier: str | None
    assembled_on: date | None
    delivered_on: date | None
    notes: str | None
    installed_count: int
    build_count: int


class WatchCreate(BaseModel):
    identifier: str | None = Field(
        default=None, description="Explicit identifier such as N1-017; generated when omitted."
    )
    product_model_ref: str = Field(description="Model identifier or id, e.g. N1.01")
    serial_number: str | None = Field(
        default=None, max_length=32, description="Defaults to the numeric part of the identifier."
    )
    status: WatchStatus = WatchStatus.PLANNED
    owner_name: str | None = Field(default=None, max_length=200)
    origin_prototype_ref: str | None = None
    assembled_on: date | None = None
    delivered_on: date | None = None
    notes: str | None = None
    is_placeholder: bool = False

    @model_validator(mode="after")
    def _serial(self) -> WatchCreate:
        if self.identifier is None and self.serial_number is not None:
            raise ValueError("serial_number is derived from the identifier; omit it or give both")
        return self


class WatchUpdate(BaseModel):
    status: WatchStatus | None = None
    owner_name: str | None = Field(default=None, max_length=200)
    origin_prototype_ref: str | None = None
    assembled_on: date | None = None
    delivered_on: date | None = None
    notes: str | None = None
    is_placeholder: bool | None = None
