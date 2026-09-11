from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from nemeth.modules.changes.models import ChangeRole, ChangeStatus
from nemeth.modules.components.schemas import AuditFields, ComponentSummary, RevisionSummary
from nemeth.modules.experiments.schemas import ExperimentSummary
from nemeth.modules.testing.schemas import TestRunSummary


class ChangeText(BaseModel):
    reason: str | None = None
    description: str | None = None
    impact: str | None = None
    notes: str | None = None


class ChangeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    title: str
    status: ChangeStatus
    requested_by: str
    approved_on: date | None
    implemented_on: date | None
    is_placeholder: bool


class ChangeRevisionLink(BaseModel):
    id: uuid.UUID
    role: ChangeRole
    revision: RevisionSummary
    component: ComponentSummary


class ChangeRead(ChangeSummary, ChangeText, AuditFields):
    approved_by: str | None
    revisions: list[ChangeRevisionLink]
    experiments: list[ExperimentSummary]
    test_runs: list[TestRunSummary]


class ChangeCreate(ChangeText):
    identifier: str | None = Field(default=None, description="Generated as ECR-NNNN when omitted.")
    title: str = Field(min_length=1, max_length=200)
    requested_by: str | None = Field(default=None, max_length=120)
    affected_revision_ids: list[uuid.UUID] = Field(default_factory=list)
    proposed_revision_ids: list[uuid.UUID] = Field(default_factory=list)
    experiment_refs: list[str] = Field(default_factory=list)
    is_placeholder: bool = False


class ChangeUpdate(ChangeText):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: ChangeStatus | None = None
    approved_by: str | None = Field(default=None, max_length=120)
    approved_on: date | None = None
    implemented_on: date | None = None
    is_placeholder: bool | None = None


class LinkRevisionRole(BaseModel):
    component_revision_id: uuid.UUID
    role: ChangeRole
