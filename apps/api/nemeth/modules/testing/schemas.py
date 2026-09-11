from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nemeth.modules.components.schemas import AuditFields, ComponentSummary, RevisionSummary
from nemeth.modules.experiments.schemas import ExperimentSummary
from nemeth.modules.prototypes.schemas import PartInstanceSummary, PrototypeSummary
from nemeth.modules.testing.models import TestOutcome
from nemeth.modules.watches.schemas import WatchSummary

# --- test types --------------------------------------------------------------------


class MetricDef(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    label: str = Field(min_length=1, max_length=80)
    unit: str | None = Field(default=None, max_length=16)


class TestTypeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    uses_positions: bool


class TestTypeRead(TestTypeSummary, AuditFields):
    description: str | None
    metrics: list[MetricDef]
    allow_custom_metrics: bool
    is_builtin: bool
    is_active: bool


class TestTypeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    metrics: list[MetricDef] = Field(default_factory=list)
    allow_custom_metrics: bool = False
    uses_positions: bool = False


class TestTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    metrics: list[MetricDef] | None = None
    allow_custom_metrics: bool | None = None
    uses_positions: bool | None = None
    is_active: bool | None = None


# --- measurements ------------------------------------------------------------------


class MeasurementCreate(BaseModel):
    metric: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    value: Decimal
    unit: str | None = Field(default=None, max_length=16)
    position: str | None = Field(default=None, max_length=8)
    recorded_at: datetime | None = None
    notes: str | None = None
    extra: dict[str, Any] | None = None


class MeasurementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: int
    metric: str
    value: Decimal
    unit: str | None
    position: str | None
    recorded_at: datetime
    notes: str | None
    extra: dict[str, Any] | None


# --- test runs ---------------------------------------------------------------------


class PositionReading(BaseModel):
    position: str
    label: str
    rate_sec_day: Decimal | None
    amplitude_deg: Decimal | None
    beat_error_ms: Decimal | None


class TimingSummary(BaseModel):
    """Per-position timegrapher readings and the classic derived figures."""

    positions: list[PositionReading]
    mean_rate_sec_day: Decimal | None
    delta_sec_day: Decimal | None = Field(
        default=None, description="Max minus min rate across positions."
    )
    min_amplitude_deg: Decimal | None
    max_amplitude_deg: Decimal | None
    max_beat_error_ms: Decimal | None
    lift_angle_deg: Decimal | None


class TestRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    title: str | None
    test_type: TestTypeSummary
    performed_at: datetime
    performed_by: str
    outcome: TestOutcome
    is_placeholder: bool


class TestRunRead(TestRunSummary, AuditFields):
    prototype: PrototypeSummary | None
    watch: WatchSummary | None
    part_instance: PartInstanceSummary | None
    revision: RevisionSummary | None
    component: ComponentSummary | None
    experiment: ExperimentSummary | None
    equipment: str | None
    conditions: dict[str, Any] | None
    notes: str | None
    measurements: list[MeasurementRead]
    timing: TimingSummary | None


class TestRunCreate(BaseModel):
    test_type_code: str = Field(min_length=2, max_length=32)
    title: str | None = Field(default=None, max_length=200)
    prototype_ref: str | None = None
    watch_ref: str | None = None
    part_instance_ref: str | None = None
    component_revision_id: uuid.UUID | None = None
    experiment_ref: str | None = None
    performed_at: datetime | None = None
    performed_by: str | None = Field(default=None, max_length=120)
    equipment: str | None = Field(default=None, max_length=200)
    conditions: dict[str, Any] | None = None
    outcome: TestOutcome = TestOutcome.INFO
    notes: str | None = None
    is_placeholder: bool = False
    measurements: list[MeasurementCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _single_subject(self) -> TestRunCreate:
        subjects = [
            self.prototype_ref,
            self.watch_ref,
            self.part_instance_ref,
            self.component_revision_id,
        ]
        if sum(1 for s in subjects if s is not None) > 1:
            raise ValueError("a test run has at most one subject")
        return self


class TestRunUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    outcome: TestOutcome | None = None
    equipment: str | None = Field(default=None, max_length=200)
    conditions: dict[str, Any] | None = None
    notes: str | None = None
    is_placeholder: bool | None = None
