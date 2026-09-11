from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.db import get_session
from nemeth.core.pagination import Page, PageParams, page_params
from nemeth.modules.components.schemas import ComponentSummary
from nemeth.modules.experiments import service as experiments
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.testing import service
from nemeth.modules.testing.models import POSITION_LABELS, POSITIONS, TestRun
from nemeth.modules.testing.schemas import (
    MeasurementCreate,
    TestRunCreate,
    TestRunRead,
    TestRunUpdate,
    TestTypeCreate,
    TestTypeRead,
    TestTypeUpdate,
    TimingSummary,
)
from nemeth.modules.watches import service as watches

router = APIRouter(tags=["testing"])


def _read(run: TestRun) -> TestRunRead:
    return TestRunRead.model_validate(
        {
            **{
                k: getattr(run, k)
                for k in TestRunRead.model_fields
                if k not in ("component", "timing")
            },
            "component": (
                ComponentSummary.model_validate(run.revision.component) if run.revision else None
            ),
            "timing": service.timing_summary(run),
        }
    )


# --- test types --------------------------------------------------------------------


@router.get("/test-types", response_model=list[TestTypeRead])
def list_test_types(
    include_inactive: bool = False, session: Session = Depends(get_session)
) -> list[TestTypeRead]:
    return [
        TestTypeRead.model_validate(t) for t in service.list_test_types(session, include_inactive)
    ]


@router.post("/test-types", response_model=TestTypeRead, status_code=status.HTTP_201_CREATED)
def create_test_type(
    payload: TestTypeCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> TestTypeRead:
    return TestTypeRead.model_validate(service.create_test_type(session, actor, payload))


@router.get("/test-types/{ref}", response_model=TestTypeRead)
def get_test_type(ref: str, session: Session = Depends(get_session)) -> TestTypeRead:
    return TestTypeRead.model_validate(service.get_test_type(session, ref))


@router.patch("/test-types/{ref}", response_model=TestTypeRead)
def update_test_type(
    ref: str,
    payload: TestTypeUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> TestTypeRead:
    test_type = service.get_test_type(session, ref)
    return TestTypeRead.model_validate(service.update_test_type(session, actor, test_type, payload))


@router.get("/test-positions", response_model=list[dict[str, str]])
def list_positions() -> list[dict[str, str]]:
    return [{"code": p, "label": POSITION_LABELS[p]} for p in POSITIONS]


# --- test runs ---------------------------------------------------------------------


@router.get("/test-runs", response_model=Page[TestRunRead])
def list_test_runs(
    test_type: str | None = Query(default=None, description="Test type code"),
    prototype_id: uuid.UUID | None = None,
    part_instance_id: uuid.UUID | None = None,
    experiment_id: uuid.UUID | None = None,
    revision_id: uuid.UUID | None = None,
    page: PageParams = Depends(page_params),
    session: Session = Depends(get_session),
) -> Page[TestRunRead]:
    items, total = service.list_test_runs(
        session,
        page,
        test_type_code=test_type,
        prototype_id=prototype_id,
        part_instance_id=part_instance_id,
        experiment_id=experiment_id,
        revision_id=revision_id,
    )
    return Page(items=[_read(r) for r in items], total=total, limit=page.limit, offset=page.offset)


@router.post("/test-runs", response_model=TestRunRead, status_code=status.HTTP_201_CREATED)
def create_test_run(
    payload: TestRunCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> TestRunRead:
    return _read(service.create_test_run(session, actor, payload))


@router.get("/test-runs/{ref}", response_model=TestRunRead)
def get_test_run(ref: str, session: Session = Depends(get_session)) -> TestRunRead:
    return _read(service.get_test_run(session, ref))


@router.patch("/test-runs/{ref}", response_model=TestRunRead)
def update_test_run(
    ref: str,
    payload: TestRunUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> TestRunRead:
    run = service.get_test_run(session, ref)
    return _read(service.update_test_run(session, actor, run, payload))


@router.post("/test-runs/{ref}/measurements", response_model=TestRunRead)
def add_measurements(
    ref: str,
    payload: list[MeasurementCreate],
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> TestRunRead:
    run = service.get_test_run(session, ref)
    return _read(service.add_measurements(session, actor, run, payload))


@router.get("/prototypes/{ref}/test-runs", response_model=list[TestRunRead])
def prototype_test_runs(ref: str, session: Session = Depends(get_session)) -> list[TestRunRead]:
    prototype = prototypes.get_prototype(session, ref)
    items, _ = service.list_test_runs(
        session, PageParams(limit=500, offset=0), prototype_id=prototype.id
    )
    return [_read(r) for r in items]


@router.get("/prototypes/{ref}/timing", response_model=TimingSummary | None)
def prototype_timing(ref: str, session: Session = Depends(get_session)) -> TimingSummary | None:
    """Timing summary of the most recent timegrapher run on this prototype."""
    prototype = prototypes.get_prototype(session, ref)
    run = service.latest_timegrapher_run(session, prototype.id)
    return service.timing_summary(run) if run else None


@router.get("/watches/{ref}/test-runs", response_model=list[TestRunRead])
def watch_test_runs(ref: str, session: Session = Depends(get_session)) -> list[TestRunRead]:
    watch = watches.get_watch(session, ref)
    items, _ = service.list_test_runs(session, PageParams(limit=500, offset=0), watch_id=watch.id)
    return [_read(r) for r in items]


@router.get("/watches/{ref}/timing", response_model=TimingSummary | None)
def watch_timing(ref: str, session: Session = Depends(get_session)) -> TimingSummary | None:
    watch = watches.get_watch(session, ref)
    run = service.latest_timegrapher_run(session, watch_id=watch.id)
    return service.timing_summary(run) if run else None


@router.get("/experiments/{ref}/test-runs", response_model=list[TestRunRead])
def experiment_test_runs(ref: str, session: Session = Depends(get_session)) -> list[TestRunRead]:
    experiment = experiments.get_experiment(session, ref)
    items, _ = service.list_test_runs(
        session, PageParams(limit=500, offset=0), experiment_id=experiment.id
    )
    return [_read(r) for r in items]


@router.get("/part-instances/{ref}/test-runs", response_model=list[TestRunRead])
def part_instance_test_runs(ref: str, session: Session = Depends(get_session)) -> list[TestRunRead]:
    instance = prototypes.get_part_instance(session, ref)
    items, _ = service.list_test_runs(
        session, PageParams(limit=500, offset=0), part_instance_id=instance.id
    )
    return [_read(r) for r in items]
