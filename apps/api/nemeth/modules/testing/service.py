"""Test types, runs and measurements: validation against the type's metric list,
subject resolution, and timegrapher summaries."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from nemeth.core.audit import stamp_created, stamp_updated
from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError, DuplicateIdentifierError, NotFoundError
from nemeth.core.identifiers import next_identifier
from nemeth.core.lookup import get_by_ref, parse_uuid
from nemeth.core.pagination import PageParams
from nemeth.modules.components import service as components
from nemeth.modules.components.models import ComponentRevision
from nemeth.modules.experiments import service as experiments
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.models import PartInstance, Prototype
from nemeth.modules.testing.models import (
    POSITION_LABELS,
    POSITIONS,
    Measurement,
    TestRun,
    TestType,
)
from nemeth.modules.testing.schemas import (
    MeasurementCreate,
    PositionReading,
    TestRunCreate,
    TestRunUpdate,
    TestTypeCreate,
    TestTypeUpdate,
    TimingSummary,
)

TIMEGRAPHER = "TIMEGRAPHER"

BUILTIN_TEST_TYPES: tuple[dict[str, object], ...] = (
    {
        "code": TIMEGRAPHER,
        "name": "Timegrapher",
        "description": "Rate, amplitude and beat error per position.",
        "uses_positions": True,
        "metrics": [
            {"key": "rate_sec_day", "label": "Rate", "unit": "s/d"},
            {"key": "amplitude_deg", "label": "Amplitude", "unit": "°"},
            {"key": "beat_error_ms", "label": "Beat error", "unit": "ms"},
            {"key": "lift_angle_deg", "label": "Lift angle", "unit": "°"},
        ],
    },
    {
        "code": "POWER_RESERVE",
        "name": "Power reserve",
        "description": "Run time from full wind to stop, with amplitude at start and end.",
        "metrics": [
            {"key": "power_reserve_h", "label": "Power reserve", "unit": "h"},
            {"key": "amplitude_start_deg", "label": "Amplitude at start", "unit": "°"},
            {"key": "amplitude_end_deg", "label": "Amplitude at end", "unit": "°"},
        ],
    },
    {
        "code": "WATER_RESISTANCE",
        "name": "Water resistance",
        "description": "Pressure test; pass/fail in the outcome, figures as measurements.",
        "metrics": [
            {"key": "test_pressure_bar", "label": "Test pressure", "unit": "bar"},
            {"key": "deflection_um", "label": "Case deflection", "unit": "µm"},
        ],
    },
    {
        "code": "DIMENSIONAL_INSPECTION",
        "name": "Dimensional inspection",
        "description": "Measured features of a part; metric keys name the feature.",
        "allow_custom_metrics": True,
        "metrics": [],
    },
    {
        "code": "TORQUE",
        "name": "Torque",
        "description": "Mainspring, crown or screw torque.",
        "metrics": [{"key": "torque_mnm", "label": "Torque", "unit": "mN·m"}],
    },
    {
        "code": "TEMPERATURE",
        "name": "Temperature",
        "description": "Rate and amplitude at a controlled temperature.",
        "uses_positions": True,
        "metrics": [
            {"key": "temperature_c", "label": "Temperature", "unit": "°C"},
            {"key": "rate_sec_day", "label": "Rate", "unit": "s/d"},
            {"key": "amplitude_deg", "label": "Amplitude", "unit": "°"},
        ],
    },
    {
        "code": "MAGNETISM",
        "name": "Magnetism",
        "description": "Residual magnetic field and its effect on rate.",
        "metrics": [
            {"key": "field_gauss", "label": "Field", "unit": "G"},
            {"key": "rate_sec_day", "label": "Rate", "unit": "s/d"},
        ],
    },
    {
        "code": "VISUAL_INSPECTION",
        "name": "Visual inspection",
        "description": "Finish, burrs, scratches, lubrication. Findings in notes; pass/fail in outcome.",
        "metrics": [],
    },
    {
        "code": "CUSTOM",
        "name": "Custom",
        "description": "Any measurement not covered by another type.",
        "allow_custom_metrics": True,
        "metrics": [],
    },
)

_RUN_OPTS = (
    selectinload(TestRun.test_type),
    selectinload(TestRun.prototype),
    selectinload(TestRun.part_instance),
    selectinload(TestRun.revision).selectinload(ComponentRevision.component),
    selectinload(TestRun.experiment),
    selectinload(TestRun.measurements),
)


# --- test types --------------------------------------------------------------------


def ensure_builtin_test_types(session: Session, actor: Actor) -> int:
    """Insert any missing built-in types. Idempotent; never overwrites edits."""
    existing = {code for (code,) in session.execute(select(TestType.code)).all()}
    created = 0
    for spec in BUILTIN_TEST_TYPES:
        if spec["code"] in existing:
            continue
        test_type = TestType(is_builtin=True, **spec)
        stamp_created(test_type, actor)
        session.add(test_type)
        created += 1
    session.flush()
    return created


def list_test_types(session: Session, include_inactive: bool = False) -> list[TestType]:
    stmt = select(TestType).order_by(TestType.is_builtin.desc(), TestType.code)
    if not include_inactive:
        stmt = stmt.where(TestType.is_active.is_(True))
    return list(session.execute(stmt).scalars())


def get_test_type(session: Session, ref: str) -> TestType:
    """Look up by code (case-insensitive) or by UUID."""
    stmt = select(TestType).where(TestType.code == ref.strip().upper())
    found = session.execute(stmt).scalar_one_or_none()
    if found is None:
        as_uuid = parse_uuid(ref)
        found = session.get(TestType, as_uuid) if as_uuid else None
    if found is None:
        raise NotFoundError(f"Test type {ref!r} not found", resource="TestType", ref=ref)
    return found


def create_test_type(session: Session, actor: Actor, data: TestTypeCreate) -> TestType:
    code = data.code.strip().upper()
    if session.execute(select(TestType.id).where(TestType.code == code)).first():
        raise DuplicateIdentifierError(f"Test type {code} already exists", identifier=code)
    test_type = TestType(
        code=code,
        name=data.name.strip(),
        description=data.description,
        metrics=[m.model_dump() for m in data.metrics],
        allow_custom_metrics=data.allow_custom_metrics,
        uses_positions=data.uses_positions,
        is_builtin=False,
    )
    stamp_created(test_type, actor)
    session.add(test_type)
    session.flush()
    return test_type


def update_test_type(
    session: Session, actor: Actor, test_type: TestType, data: TestTypeUpdate
) -> TestType:
    changes = data.model_dump(exclude_unset=True)
    if "metrics" in changes and changes["metrics"] is not None:
        changes["metrics"] = [m.model_dump() for m in data.metrics or []]
    for field, value in changes.items():
        if value is None and field != "description":
            continue
        setattr(test_type, field, value)
    stamp_updated(test_type, actor)
    session.flush()
    return test_type


# --- test runs ---------------------------------------------------------------------


def _run_exists(session: Session, identifier: str) -> bool:
    stmt = select(func.count()).select_from(TestRun).where(TestRun.identifier == identifier)
    return bool(session.execute(stmt).scalar_one())


def get_test_run(session: Session, ref: str) -> TestRun:
    return get_by_ref(session, TestRun, ref, options=_RUN_OPTS, label="TestRun")


def list_test_runs(
    session: Session,
    page: PageParams,
    *,
    test_type_code: str | None = None,
    prototype_id: uuid.UUID | None = None,
    part_instance_id: uuid.UUID | None = None,
    experiment_id: uuid.UUID | None = None,
    revision_id: uuid.UUID | None = None,
) -> tuple[list[TestRun], int]:
    stmt = select(TestRun)
    if test_type_code:
        stmt = stmt.join(TestType).where(TestType.code == test_type_code.strip().upper())
    if prototype_id is not None:
        stmt = stmt.where(TestRun.prototype_id == prototype_id)
    if part_instance_id is not None:
        stmt = stmt.where(TestRun.part_instance_id == part_instance_id)
    if experiment_id is not None:
        stmt = stmt.where(TestRun.experiment_id == experiment_id)
    if revision_id is not None:
        stmt = stmt.where(TestRun.component_revision_id == revision_id)
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = (
        stmt.options(*_RUN_OPTS)
        .order_by(TestRun.performed_at.desc(), TestRun.created_at.desc())
        .limit(page.limit)
        .offset(page.offset)
    )
    return list(session.execute(stmt).scalars().unique()), int(total)


def _validate_measurement(
    test_type: TestType, data: MeasurementCreate
) -> tuple[str, str | None, str | None]:
    units = test_type.metric_units()
    if data.metric not in units and not test_type.allow_custom_metrics:
        known = ", ".join(sorted(units)) or "none"
        raise DomainValidationError(
            f"Metric {data.metric!r} is not defined for {test_type.code}. Known metrics: {known}.",
            field="measurements",
            metric=data.metric,
        )
    unit = data.unit if data.unit is not None else units.get(data.metric)
    position = data.position.strip().upper() if data.position else None
    if position and test_type.uses_positions and position not in POSITIONS:
        raise DomainValidationError(
            f"Position {position!r} is not one of {', '.join(POSITIONS)}",
            field="measurements",
        )
    return data.metric, unit, position


def _append_measurements(
    run: TestRun, actor: Actor, items: list[MeasurementCreate], start_sequence: int
) -> None:
    now = datetime.now(tz=UTC)
    for offset, item in enumerate(items):
        metric, unit, position = _validate_measurement(run.test_type, item)
        row = Measurement(
            sequence=start_sequence + offset,
            metric=metric,
            value=item.value,
            unit=unit,
            position=position,
            recorded_at=item.recorded_at or run.performed_at or now,
            notes=item.notes,
            extra=item.extra,
        )
        stamp_created(row, actor)
        run.measurements.append(row)


def create_test_run(session: Session, actor: Actor, data: TestRunCreate) -> TestRun:
    test_type = get_test_type(session, data.test_type_code)
    if not test_type.is_active:
        raise DomainValidationError(
            f"Test type {test_type.code} is inactive", field="test_type_code"
        )

    prototype: Prototype | None = None
    instance: PartInstance | None = None
    revision: ComponentRevision | None = None
    if data.prototype_ref:
        prototype = prototypes.get_prototype(session, data.prototype_ref)
    if data.part_instance_ref:
        instance = prototypes.get_part_instance(session, data.part_instance_ref)
    if data.component_revision_id:
        revision = components.get_revision(session, data.component_revision_id)
    experiment = (
        experiments.get_experiment(session, data.experiment_ref) if data.experiment_ref else None
    )

    identifier = next_identifier(session, "TR", exists=lambda c: _run_exists(session, c), width=5)
    run = TestRun(
        identifier=identifier,
        test_type_id=test_type.id,
        title=data.title.strip() if data.title else None,
        prototype_id=prototype.id if prototype else None,
        part_instance_id=instance.id if instance else None,
        component_revision_id=revision.id if revision else None,
        experiment_id=experiment.id if experiment else None,
        performed_at=data.performed_at or datetime.now(tz=UTC),
        performed_by=(data.performed_by or actor.display_name).strip(),
        equipment=data.equipment,
        conditions=data.conditions,
        outcome=data.outcome,
        notes=data.notes,
        is_placeholder=data.is_placeholder,
    )
    run.test_type = test_type
    stamp_created(run, actor)
    session.add(run)
    _append_measurements(run, actor, data.measurements, 1)
    session.flush()
    return get_test_run(session, str(run.id))


def add_measurements(
    session: Session, actor: Actor, run: TestRun, items: list[MeasurementCreate]
) -> TestRun:
    start = max((m.sequence for m in run.measurements), default=0) + 1
    _append_measurements(run, actor, items, start)
    stamp_updated(run, actor)
    session.flush()
    return get_test_run(session, str(run.id))


def update_test_run(session: Session, actor: Actor, run: TestRun, data: TestRunUpdate) -> TestRun:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(run, field, value)
    stamp_updated(run, actor)
    session.flush()
    return run


# --- summaries ---------------------------------------------------------------------


def _latest_by_position(run: TestRun, metric: str) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for m in run.measurements:  # ordered by sequence; later readings win
        if m.metric == metric and m.position:
            out[m.position] = m.value
    return out


def timing_summary(run: TestRun) -> TimingSummary | None:
    if run.test_type.code != TIMEGRAPHER:
        return None
    rates = _latest_by_position(run, "rate_sec_day")
    amps = _latest_by_position(run, "amplitude_deg")
    beats = _latest_by_position(run, "beat_error_ms")
    lift = next((m.value for m in run.measurements if m.metric == "lift_angle_deg"), None)
    seen = [p for p in POSITIONS if p in rates or p in amps or p in beats]
    seen += sorted({*rates, *amps, *beats} - set(POSITIONS))
    positions = [
        PositionReading(
            position=p,
            label=POSITION_LABELS.get(p, p),
            rate_sec_day=rates.get(p),
            amplitude_deg=amps.get(p),
            beat_error_ms=beats.get(p),
        )
        for p in seen
    ]
    rate_values = list(rates.values())
    amp_values = list(amps.values())
    beat_values = list(beats.values())
    mean = (
        (sum(rate_values, Decimal(0)) / len(rate_values)).quantize(Decimal("0.1"))
        if rate_values
        else None
    )
    return TimingSummary(
        positions=positions,
        mean_rate_sec_day=mean,
        delta_sec_day=(max(rate_values) - min(rate_values)) if rate_values else None,
        min_amplitude_deg=min(amp_values) if amp_values else None,
        max_amplitude_deg=max(amp_values) if amp_values else None,
        max_beat_error_ms=max(beat_values) if beat_values else None,
        lift_angle_deg=lift,
    )


def latest_timegrapher_run(
    session: Session, prototype_id: uuid.UUID | None = None
) -> TestRun | None:
    stmt = (
        select(TestRun)
        .join(TestType)
        .where(TestType.code == TIMEGRAPHER)
        .options(*_RUN_OPTS)
        .order_by(TestRun.performed_at.desc(), TestRun.created_at.desc())
        .limit(1)
    )
    if prototype_id is not None:
        stmt = stmt.where(TestRun.prototype_id == prototype_id)
    return session.execute(stmt).scalars().unique().first()


def recent_runs(session: Session, limit: int = 6) -> list[TestRun]:
    stmt = (
        select(TestRun)
        .options(*_RUN_OPTS)
        .order_by(TestRun.performed_at.desc(), TestRun.created_at.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars().unique())


def run_count(session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(TestRun)).scalar_one())
