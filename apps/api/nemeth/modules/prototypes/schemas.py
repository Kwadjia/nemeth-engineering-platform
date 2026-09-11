from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nemeth.modules.components.schemas import AuditFields, ComponentSummary, RevisionSummary
from nemeth.modules.products.schemas import CaliberSummary, ProductModelSummary
from nemeth.modules.prototypes.models import (
    BuildAction,
    PartInstanceStatus,
    PartSource,
    PrototypeStatus,
)

# --- prototypes --------------------------------------------------------------------


class PrototypeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    name: str
    status: PrototypeStatus
    is_placeholder: bool


class PrototypeRead(PrototypeSummary, AuditFields):
    purpose: str | None
    product_model: ProductModelSummary | None
    caliber: CaliberSummary | None
    started_on: date | None
    retired_on: date | None
    notes: str | None
    installed_count: int
    build_count: int


class PrototypeCreate(BaseModel):
    identifier: str | None = Field(
        default=None, description="Explicit identifier such as N1-P003; generated when omitted."
    )
    product_code: str | None = Field(default=None, description="Used to generate {CODE}-P{NNN}.")
    name: str = Field(min_length=1, max_length=200)
    purpose: str | None = None
    status: PrototypeStatus = PrototypeStatus.PLANNED
    product_model_id: uuid.UUID | None = None
    caliber_id: uuid.UUID | None = None
    started_on: date | None = None
    notes: str | None = None
    is_placeholder: bool = False

    @model_validator(mode="after")
    def _identifier_or_product_code(self) -> PrototypeCreate:
        if self.identifier is None and self.product_code is None:
            raise ValueError("either identifier or product_code is required")
        return self


class PrototypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    purpose: str | None = None
    status: PrototypeStatus | None = None
    product_model_id: uuid.UUID | None = None
    caliber_id: uuid.UUID | None = None
    started_on: date | None = None
    retired_on: date | None = None
    notes: str | None = None
    is_placeholder: bool | None = None


# --- part instances ----------------------------------------------------------------


class PartInstanceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    serial_number: str | None
    status: PartInstanceStatus
    source: PartSource
    is_placeholder: bool


class PartInstanceRead(PartInstanceSummary, AuditFields):
    component: ComponentSummary
    revision: RevisionSummary
    lot: str | None
    material_lot: str | None
    heat_treatment_lot: str | None
    supplier_note: str | None
    notes: str | None
    current_prototype: PrototypeSummary | None


class PartInstanceCreate(BaseModel):
    component_revision_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=100, description="Create this many instances.")
    serial_number: str | None = Field(default=None, max_length=120)
    lot: str | None = Field(default=None, max_length=120)
    source: PartSource = PartSource.IN_HOUSE
    material_lot: str | None = Field(default=None, max_length=120)
    heat_treatment_lot: str | None = Field(default=None, max_length=120)
    supplier_note: str | None = Field(default=None, max_length=300)
    notes: str | None = None
    is_placeholder: bool = False


class PartInstanceUpdate(BaseModel):
    serial_number: str | None = Field(default=None, max_length=120)
    lot: str | None = Field(default=None, max_length=120)
    source: PartSource | None = None
    material_lot: str | None = Field(default=None, max_length=120)
    heat_treatment_lot: str | None = Field(default=None, max_length=120)
    supplier_note: str | None = Field(default=None, max_length=300)
    notes: str | None = None
    is_placeholder: bool | None = None


# --- build records -----------------------------------------------------------------


class BuildEntryCreate(BaseModel):
    part_instance_id: uuid.UUID | None = None
    part_instance_identifier: str | None = None
    action: BuildAction = BuildAction.INSTALL
    position: str | None = Field(default=None, max_length=120)
    notes: str | None = None

    @model_validator(mode="after")
    def _instance_ref(self) -> BuildEntryCreate:
        if self.part_instance_id is None and self.part_instance_identifier is None:
            raise ValueError("either part_instance_id or part_instance_identifier is required")
        return self


class BuildEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: int
    action: BuildAction
    position: str | None
    notes: str | None
    part_instance: PartInstanceSummary
    component: ComponentSummary
    revision: RevisionSummary


class BuildRecordSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    title: str
    performed_on: date
    performed_by: str


class BuildRecordRead(BuildRecordSummary, AuditFields):
    prototype: PrototypeSummary
    procedure: str | None
    notes: str | None
    entries: list[BuildEntryRead]


class BuildRecordCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    performed_on: date
    performed_by: str | None = Field(
        default=None, max_length=120, description="Defaults to the current actor."
    )
    procedure: str | None = Field(
        default=None, description="Steps, lubrication, torque and sequence as performed."
    )
    notes: str | None = None
    entries: list[BuildEntryCreate] = Field(default_factory=list)


class BuildRecordUpdate(BaseModel):
    notes: str | None = None


# --- configuration -----------------------------------------------------------------


class ConfigurationRow(BaseModel):
    part_instance: PartInstanceSummary
    component: ComponentSummary
    revision: RevisionSummary
    position: str | None
    installed_by: BuildRecordSummary | None


class PrototypeConfiguration(BaseModel):
    prototype: PrototypeSummary
    count: int
    rows: list[ConfigurationRow]
