from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nemeth.modules.components.schemas import AuditFields, ComponentSummary, RevisionSummary

ResolveMode = Literal["latest", "released"]
ResolutionSource = Literal["pinned", "latest", "released", "unresolved"]


class BomLineCreate(BaseModel):
    child_component_id: uuid.UUID | None = None
    child_component_identifier: str | None = None
    child_revision_id: uuid.UUID | None = Field(
        default=None, description="Pin to an exact child revision. Null resolves at query time."
    )
    find_number: int | None = Field(default=None, ge=1, description="Defaults to max + 10.")
    quantity: Decimal = Field(default=Decimal(1), gt=0)
    unit: str = Field(default="ea", max_length=16)
    reference_designator: str | None = Field(default=None, max_length=120)
    notes: str | None = None

    @model_validator(mode="after")
    def _child_ref(self) -> BomLineCreate:
        if self.child_component_id is None and self.child_component_identifier is None:
            raise ValueError("either child_component_id or child_component_identifier is required")
        return self


class BomLineUpdate(BaseModel):
    child_revision_id: uuid.UUID | None = None
    find_number: int | None = Field(default=None, ge=1)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=16)
    reference_designator: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class BomLineRead(AuditFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_revision_id: uuid.UUID
    find_number: int
    quantity: Decimal
    unit: str
    reference_designator: str | None
    notes: str | None
    is_pinned: bool
    child_component: ComponentSummary
    child_revision: RevisionSummary | None


class BomNode(BaseModel):
    line: BomLineRead
    resolved_revision: RevisionSummary | None
    resolution: ResolutionSource
    level: int
    children: list[BomNode]


class BomTree(BaseModel):
    root_component: ComponentSummary
    root_revision: RevisionSummary
    mode: ResolveMode
    line_count: int
    unresolved_count: int
    max_depth: int
    nodes: list[BomNode]


class BomFlatRow(BaseModel):
    level: int
    path: list[str]
    find_number: int
    component: ComponentSummary
    revision: RevisionSummary | None
    resolution: ResolutionSource
    is_pinned: bool
    quantity: Decimal
    extended_quantity: Decimal
    unit: str
    reference_designator: str | None


class BomFlat(BaseModel):
    root_component: ComponentSummary
    root_revision: RevisionSummary
    mode: ResolveMode
    rows: list[BomFlatRow]


class WhereUsedRow(BaseModel):
    parent_component: ComponentSummary
    parent_revision: RevisionSummary
    line: BomLineRead
