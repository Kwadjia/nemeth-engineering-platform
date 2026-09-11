from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nemeth.core.lifecycle import LifecycleState
from nemeth.core.schemas import AuditFields as AuditFields
from nemeth.modules.components.models import ComponentFamily, ComponentKind
from nemeth.modules.suppliers.schemas import SupplierSummary

# --- revisions ---------------------------------------------------------------------


class RevisionContent(BaseModel):
    """Editable engineering content of a revision. Every field optional."""

    description: str | None = None
    material: str | None = Field(default=None, max_length=200)
    heat_treatment: str | None = Field(default=None, max_length=200)
    finish: str | None = Field(default=None, max_length=200)
    manufacturing_method: str | None = Field(default=None, max_length=200)
    dimensions: dict[str, Any] | None = None
    tolerances: dict[str, Any] | None = None
    mass_g: Decimal | None = Field(default=None, ge=0)
    supplier_note: str | None = Field(default=None, max_length=300)
    supplier_id: uuid.UUID | None = None
    inspection_requirements: str | None = None
    notes: str | None = None


class RevisionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    revision_number: int
    revision_label: str
    lifecycle_state: LifecycleState
    is_frozen: bool
    frozen_at: datetime | None
    change_summary: str | None
    created_at: datetime


class ComponentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    name: str
    kind: ComponentKind
    family: ComponentFamily
    is_placeholder: bool


class RevisionRead(RevisionSummary, RevisionContent, AuditFields):
    component: ComponentSummary
    display_identifier: str
    superseded_by_id: uuid.UUID | None
    allowed_transitions: list[LifecycleState]
    supplier: SupplierSummary | None = None


class RevisionCreate(BaseModel):
    change_summary: str = Field(min_length=1, max_length=2000)
    from_revision_id: uuid.UUID | None = Field(
        default=None, description="Source revision to copy from. Defaults to the latest."
    )
    content: RevisionContent | None = Field(
        default=None, description="Overrides applied on top of the copied content."
    )
    copy_bom: bool = Field(default=True, description="Copy the source revision's BOM lines.")


class RevisionUpdate(RevisionContent):
    change_summary: str | None = Field(default=None, max_length=2000)


class TransitionRequest(BaseModel):
    target_state: LifecycleState


# --- components --------------------------------------------------------------------


class ComponentCreate(BaseModel):
    identifier: str | None = Field(
        default=None,
        description="Explicit identifier such as N1-MVT-002. Generated from product_code + family when omitted.",
    )
    product_code: str | None = Field(
        default=None, description="Product code used to generate an identifier, e.g. N1."
    )
    name: str = Field(min_length=1, max_length=200)
    kind: ComponentKind
    family: ComponentFamily
    description: str | None = None
    is_placeholder: bool = False
    initial_revision: RevisionContent | None = None
    change_summary: str = Field(default="Initial revision", max_length=2000)

    @model_validator(mode="after")
    def _identifier_or_product_code(self) -> ComponentCreate:
        if self.identifier is None and self.product_code is None:
            raise ValueError("either identifier or product_code is required")
        return self


class ComponentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    is_placeholder: bool | None = None


class ComponentRead(ComponentSummary, AuditFields):
    description: str | None
    latest_revision: RevisionSummary | None
    released_revision: RevisionSummary | None
    revision_count: int


class ComponentDetail(ComponentRead):
    revisions: list[RevisionSummary]
