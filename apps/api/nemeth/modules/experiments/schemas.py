from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from nemeth.modules.components.schemas import AuditFields, ComponentSummary, RevisionSummary
from nemeth.modules.experiments.models import ExperimentOutcome, ExperimentStatus
from nemeth.modules.prototypes.schemas import PrototypeSummary


class ExperimentText(BaseModel):
    """The notebook sections. Every field optional so a page can be saved as it grows."""

    objective: str | None = None
    hypothesis: str | None = None
    configuration: str | None = None
    methodology: str | None = None
    equipment: str | None = None
    procedure: str | None = None
    observations: str | None = None
    results: str | None = None
    conclusion: str | None = None
    follow_up: str | None = None
    notes: str | None = None


class ExperimentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    title: str
    status: ExperimentStatus
    outcome: ExperimentOutcome | None
    started_on: date | None
    completed_on: date | None
    is_placeholder: bool


class ExperimentPrototypeLink(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str | None
    prototype: PrototypeSummary


class ExperimentRevisionLink(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str | None
    revision: RevisionSummary
    component: ComponentSummary


class ExperimentRead(ExperimentSummary, ExperimentText, AuditFields):
    prototypes: list[ExperimentPrototypeLink]
    revisions: list[ExperimentRevisionLink]


class ExperimentCreate(ExperimentText):
    identifier: str | None = Field(default=None, description="Generated as EXP-NNN when omitted.")
    title: str = Field(min_length=1, max_length=200)
    status: ExperimentStatus = ExperimentStatus.PLANNED
    started_on: date | None = None
    is_placeholder: bool = False
    prototype_ids: list[uuid.UUID] = Field(default_factory=list)


class ExperimentUpdate(ExperimentText):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: ExperimentStatus | None = None
    outcome: ExperimentOutcome | None = None
    started_on: date | None = None
    completed_on: date | None = None
    is_placeholder: bool | None = None


class LinkPrototype(BaseModel):
    prototype_id: uuid.UUID | None = None
    prototype_identifier: str | None = None
    role: str | None = Field(default=None, max_length=80)


class LinkRevision(BaseModel):
    component_revision_id: uuid.UUID
    role: str | None = Field(default=None, max_length=80)
