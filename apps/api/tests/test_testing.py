"""Test types, test runs, measurements and timing summaries."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError
from nemeth.core.pagination import PageParams
from nemeth.modules.experiments import service as experiments
from nemeth.modules.experiments.schemas import ExperimentCreate
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.schemas import PrototypeCreate
from nemeth.modules.testing import service
from nemeth.modules.testing.models import TestOutcome
from nemeth.modules.testing.schemas import (
    MeasurementCreate,
    MetricDef,
    TestRunCreate,
    TestTypeCreate,
)
from nemeth.seed.n1 import seed_n1


@pytest.fixture(autouse=True)
def builtin_types(session: Session, actor: Actor) -> None:
    service.ensure_builtin_test_types(session, actor)


def _timegrapher(prototype_ref: str | None = None, **extra: object) -> TestRunCreate:
    readings = {
        "DU": ("2.8", "287", "0.1"),
        "DD": ("3.4", "281", "0.2"),
        "CU": ("-1.2", "252", "0.3"),
        "CD": ("0.6", "258", "0.1"),
        "CL": ("1.9", "261", "0.2"),
        "CR": ("-0.4", "255", "0.4"),
    }
    measurements = [MeasurementCreate(metric="lift_angle_deg", value=Decimal("44"))]
    for position, (rate, amp, beat) in readings.items():
        measurements += [
            MeasurementCreate(metric="rate_sec_day", value=Decimal(rate), position=position),
            MeasurementCreate(metric="amplitude_deg", value=Decimal(amp), position=position),
            MeasurementCreate(metric="beat_error_ms", value=Decimal(beat), position=position),
        ]
    return TestRunCreate(
        test_type_code="timegrapher",
        title="Baseline",
        prototype_ref=prototype_ref,
        equipment="Weishi 1000",
        conditions={"temperature_c": 22.5, "state_of_wind": "full"},
        measurements=measurements,
        **extra,  # type: ignore[arg-type]
    )


def test_builtin_types_are_seeded_once(session: Session, actor: Actor) -> None:
    assert service.ensure_builtin_test_types(session, actor) == 0
    codes = [t.code for t in service.list_test_types(session)]
    assert codes[:1] == ["CUSTOM"] or "TIMEGRAPHER" in codes
    timegrapher = service.get_test_type(session, "timegrapher")
    assert timegrapher.uses_positions and timegrapher.is_builtin
    assert timegrapher.metric_units()["rate_sec_day"] == "s/d"


def test_timegrapher_run_and_summary(session: Session, actor: Actor) -> None:
    prototype = prototypes.create_prototype(
        session, actor, PrototypeCreate(product_code="T1", name="P")
    )
    run = service.create_test_run(session, actor, _timegrapher(prototype.identifier))
    assert run.identifier == "TR-00001"
    assert run.performed_by == "Test User"
    assert len(run.measurements) == 19
    assert run.measurements[1].unit == "s/d"  # unit defaulted from the metric definition

    summary = service.timing_summary(run)
    assert summary is not None
    assert [p.position for p in summary.positions] == ["DU", "DD", "CU", "CD", "CL", "CR"]
    assert summary.positions[0].label == "Dial up"
    assert summary.delta_sec_day == Decimal("4.6")  # 3.4 - (-1.2)
    assert summary.mean_rate_sec_day == Decimal("1.2")
    assert summary.min_amplitude_deg == Decimal("252")
    assert summary.max_amplitude_deg == Decimal("287")
    assert summary.max_beat_error_ms == Decimal("0.4")
    assert summary.lift_angle_deg == Decimal("44")

    latest = service.latest_timegrapher_run(session, prototype.id)
    assert latest is not None and latest.id == run.id


def test_unknown_metric_and_bad_position_are_rejected(session: Session, actor: Actor) -> None:
    with pytest.raises(DomainValidationError):
        service.create_test_run(
            session,
            actor,
            TestRunCreate(
                test_type_code="TIMEGRAPHER",
                measurements=[MeasurementCreate(metric="torque_mnm", value=Decimal(1))],
            ),
        )
    with pytest.raises(DomainValidationError):
        service.create_test_run(
            session,
            actor,
            TestRunCreate(
                test_type_code="TIMEGRAPHER",
                measurements=[
                    MeasurementCreate(metric="rate_sec_day", value=Decimal(1), position="UP")
                ],
            ),
        )
    # Dimensional inspection accepts any feature name as a metric.
    run = service.create_test_run(
        session,
        actor,
        TestRunCreate(
            test_type_code="DIMENSIONAL_INSPECTION",
            measurements=[
                MeasurementCreate(metric="pivot_diameter_mm", value=Decimal("0.1200"), unit="mm")
            ],
        ),
    )
    assert run.measurements[0].metric == "pivot_diameter_mm"
    assert service.timing_summary(run) is None


def test_custom_test_type_and_appending(session: Session, actor: Actor) -> None:
    created = service.create_test_type(
        session,
        actor,
        TestTypeCreate(
            code="hairspring_pin",
            name="Hairspring pinning",
            metrics=[MetricDef(key="active_length_mm", label="Active length", unit="mm")],
        ),
    )
    assert created.code == "HAIRSPRING_PIN" and not created.is_builtin
    run = service.create_test_run(session, actor, TestRunCreate(test_type_code="HAIRSPRING_PIN"))
    run = service.add_measurements(
        session, actor, run, [MeasurementCreate(metric="active_length_mm", value=Decimal("31.2"))]
    )
    run = service.add_measurements(
        session, actor, run, [MeasurementCreate(metric="active_length_mm", value=Decimal("31.4"))]
    )
    assert [m.sequence for m in run.measurements] == [1, 2]
    assert run.measurements[1].unit == "mm"


def test_at_most_one_subject_and_experiment_link(session: Session, actor: Actor) -> None:
    prototype = prototypes.create_prototype(
        session, actor, PrototypeCreate(product_code="T1", name="P")
    )
    experiment = experiments.create_experiment(session, actor, ExperimentCreate(title="Timing"))
    with pytest.raises(ValueError):
        TestRunCreate(
            test_type_code="TIMEGRAPHER", prototype_ref="T1-P001", part_instance_ref="PI-00001"
        )
    run = service.create_test_run(
        session,
        actor,
        TestRunCreate(
            test_type_code="VISUAL_INSPECTION",
            prototype_ref="t1-p001",
            experiment_ref="exp-001",
            outcome=TestOutcome.FAIL,
            notes="Burr on bridge",
        ),
    )
    assert run.prototype is not None and run.prototype.id == prototype.id
    assert run.experiment is not None and run.experiment.id == experiment.id
    items, total = service.list_test_runs(
        session, PageParams(limit=10, offset=0), experiment_id=experiment.id
    )
    assert total == 1 and items[0].outcome is TestOutcome.FAIL


def test_seed_installs_builtin_types(session: Session) -> None:
    seed_n1(session)
    assert len(service.list_test_types(session)) >= 9


def test_api_timegrapher_flow(client: TestClient, session: Session, actor: Actor) -> None:
    prototypes.create_prototype(session, actor, PrototypeCreate(product_code="T1", name="P"))
    payload = _timegrapher("T1-P001").model_dump(mode="json")
    created = client.post("/api/v1/test-runs", json=payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["identifier"] == "TR-00001" and body["test_type"]["code"] == "TIMEGRAPHER"
    assert body["timing"]["delta_sec_day"] == "4.6"
    assert body["prototype"]["identifier"] == "T1-P001"

    timing = client.get("/api/v1/prototypes/T1-P001/timing").json()
    assert (
        timing["positions"][0]["position"] == "DU"
        and timing["positions"][0]["amplitude_deg"] == "287"
    )

    bad = client.post("/api/v1/test-runs", json={"test_type_code": "NOPE"})
    assert bad.status_code == 404

    types = client.get("/api/v1/test-types").json()
    assert any(t["code"] == "TIMEGRAPHER" for t in types)
    positions = client.get("/api/v1/test-positions").json()
    assert positions[0] == {"code": "DU", "label": "Dial up"}

    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["latest_timing"]["mean_rate_sec_day"] == "1.2"
    assert summary["recent_test_runs"][0]["identifier"] == "TR-00001"
    assert summary["test_run_count"] == 1

    now = datetime.now(tz=UTC).isoformat()
    added = client.post(
        "/api/v1/test-runs/TR-00001/measurements",
        json=[{"metric": "rate_sec_day", "value": "5.0", "position": "du", "recorded_at": now}],
    )
    assert added.status_code == 200
    assert added.json()["timing"]["positions"][0]["rate_sec_day"] == "5.0"  # later reading wins
