from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from nemeth import __version__
from nemeth.core.auth import Actor, get_actor
from nemeth.core.config import Settings, get_settings
from nemeth.core.db import get_session
from nemeth.modules.bom import service as bom
from nemeth.modules.components import service as components
from nemeth.modules.components.schemas import ComponentSummary, RevisionSummary
from nemeth.modules.experiments import service as experiments
from nemeth.modules.experiments.schemas import ExperimentSummary
from nemeth.modules.products import service as products
from nemeth.modules.products.schemas import CaliberSummary, ProductSummary
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.schemas import PrototypeSummary
from nemeth.modules.testing import service as testing
from nemeth.modules.testing.schemas import TestRunSummary, TimingSummary
from nemeth.modules.watches import service as watches
from nemeth.modules.watches.schemas import WatchSummary

log = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


class Health(BaseModel):
    status: str
    version: str
    environment: str
    database: str


class SystemInfo(BaseModel):
    app_name: str
    version: str
    environment: str
    api_prefix: str
    storage_backend: str
    storage_root: str
    actor_id: str
    actor_name: str


class RecentRevision(RevisionSummary):
    component: ComponentSummary


class DashboardSummary(BaseModel):
    products: list[ProductSummary]
    calibers: list[CaliberSummary]
    component_count: int
    assembly_count: int
    components_by_state: dict[str, int]
    recent_revisions: list[RecentRevision]
    prototype_count: int
    active_prototype: PrototypeSummary | None
    prototypes: list[PrototypeSummary]
    recent_experiments: list[ExperimentSummary]
    experiments_by_status: dict[str, int]
    test_run_count: int
    recent_test_runs: list[TestRunSummary]
    latest_timing: TimingSummary | None
    latest_timing_run: TestRunSummary | None
    watch_count: int
    watches: list[WatchSummary]


@router.get("/health", response_model=Health)
def health(
    session: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> Health:
    try:
        session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # pragma: no cover - only reachable when the database is down
        log.exception("database health check failed")
        database = "error"
    return Health(
        status="ok" if database == "ok" else "degraded",
        version=__version__,
        environment=settings.environment,
        database=database,
    )


@router.get("/system/info", response_model=SystemInfo)
def system_info(
    settings: Settings = Depends(get_settings), actor: Actor = Depends(get_actor)
) -> SystemInfo:
    return SystemInfo(
        app_name=settings.app_name,
        version=__version__,
        environment=settings.environment,
        api_prefix=settings.api_prefix,
        storage_backend=settings.storage_backend,
        storage_root=str(settings.storage_root),
        actor_id=actor.id,
        actor_name=actor.display_name,
    )


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(session: Session = Depends(get_session)) -> DashboardSummary:
    from nemeth.core.pagination import PageParams

    product_items, _ = products.list_products(session, PageParams(limit=20, offset=0))
    caliber_items, _ = products.list_calibers(session, PageParams(limit=20, offset=0))
    by_state = components.count_by_state(session)
    recent = components.recent_revisions(session, limit=8)
    active = prototypes.active_prototype(session)
    latest_run = testing.latest_timegrapher_run(session)
    watch_items, _ = watches.list_watches(session, PageParams(limit=6, offset=0))
    proto_items, proto_total = prototypes.list_prototypes(session, PageParams(limit=6, offset=0))
    return DashboardSummary(
        products=[ProductSummary.model_validate(p) for p in product_items],
        calibers=[CaliberSummary.model_validate(c) for c in caliber_items],
        component_count=sum(by_state.values()),
        assembly_count=bom.assembly_count(session),
        components_by_state=by_state,
        recent_revisions=[
            RecentRevision(
                **RevisionSummary.model_validate(r).model_dump(),
                component=ComponentSummary.model_validate(r.component),
            )
            for r in recent
        ],
        prototype_count=proto_total,
        active_prototype=PrototypeSummary.model_validate(active) if active else None,
        prototypes=[PrototypeSummary.model_validate(p) for p in proto_items],
        recent_experiments=[
            ExperimentSummary.model_validate(e) for e in experiments.recent(session, 5)
        ],
        experiments_by_status=experiments.count_by_status(session),
        test_run_count=testing.run_count(session),
        recent_test_runs=[TestRunSummary.model_validate(r) for r in testing.recent_runs(session)],
        latest_timing=testing.timing_summary(latest_run) if latest_run else None,
        latest_timing_run=TestRunSummary.model_validate(latest_run) if latest_run else None,
        watch_count=watches.count(session),
        watches=[WatchSummary.model_validate(w) for w in watch_items],
    )
