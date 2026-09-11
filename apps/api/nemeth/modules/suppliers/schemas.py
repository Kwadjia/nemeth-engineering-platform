from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from nemeth.core.schemas import AuditFields
from nemeth.modules.suppliers.models import SupplierKind


class SupplierSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    name: str
    kind: SupplierKind
    is_active: bool


class SupplierRead(SupplierSummary, AuditFields):
    capabilities: str | None
    contact_name: str | None
    email: str | None
    phone: str | None
    website: str | None
    address: str | None
    country: str | None
    notes: str | None
    is_placeholder: bool


class SupplierCreate(BaseModel):
    identifier: str | None = Field(default=None, description="Generated as SUP-NNN when omitted.")
    name: str = Field(min_length=1, max_length=200)
    kind: SupplierKind = SupplierKind.OTHER
    capabilities: str | None = None
    contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=60)
    website: str | None = Field(default=None, max_length=300)
    address: str | None = None
    country: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    is_placeholder: bool = False


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: SupplierKind | None = None
    capabilities: str | None = None
    contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=60)
    website: str | None = Field(default=None, max_length=300)
    address: str | None = None
    country: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    is_active: bool | None = None
    is_placeholder: bool | None = None
