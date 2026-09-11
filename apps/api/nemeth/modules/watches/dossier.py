"""The dossier: everything known about one serialized watch, assembled in one document.

This is the "digital build record" and the read model a future AI assistant or public
provenance page would consume.
"""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.orm import Session

from nemeth.core.pagination import PageParams
from nemeth.modules.experiments import service as experiments
from nemeth.modules.experiments.schemas import ExperimentSummary
from nemeth.modules.products.schemas import CaliberSummary, ProductModelSummary, ProductSummary
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.schemas import BuildRecordRead, PrototypeSummary, UnitConfiguration
from nemeth.modules.testing import service as testing
from nemeth.modules.testing.schemas import TestRunSummary, TimingSummary
from nemeth.modules.watches.models import Watch
from nemeth.modules.watches.schemas import WatchRead


class WatchDossier(BaseModel):
    watch: WatchRead
    product: ProductSummary
    model: ProductModelSummary
    caliber: CaliberSummary | None
    origin_prototype: PrototypeSummary | None
    configuration: UnitConfiguration
    build_records: list[BuildRecordRead]
    test_runs: list[TestRunSummary]
    latest_timing: TimingSummary | None
    latest_timing_run: TestRunSummary | None
    experiments: list[ExperimentSummary]


def build_dossier(session: Session, watch: Watch) -> WatchDossier:
    runs, _ = testing.list_test_runs(
        session,
        PageParams(limit=500, offset=0),
        watch_id=watch.id,
    )
    latest = testing.latest_timegrapher_run(session, watch_id=watch.id)
    related_experiments: list[ExperimentSummary] = []
    if watch.origin_prototype is not None:
        items, _ = experiments.list_experiments(
            session,
            PageParams(limit=200, offset=0),
            prototype_id=watch.origin_prototype.id,
        )
        related_experiments = [ExperimentSummary.model_validate(e) for e in items]
    return WatchDossier(
        watch=WatchRead.model_validate(
            {
                **{
                    k: getattr(watch, k)
                    for k in WatchRead.model_fields
                    if k != "origin_prototype_identifier"
                },
                "origin_prototype_identifier": (
                    watch.origin_prototype.identifier if watch.origin_prototype else None
                ),
            }
        ),
        product=ProductSummary.model_validate(watch.product_model.product),
        model=ProductModelSummary.model_validate(watch.product_model),
        caliber=(
            CaliberSummary.model_validate(watch.product_model.caliber)
            if watch.product_model.caliber
            else None
        ),
        origin_prototype=(
            PrototypeSummary.model_validate(watch.origin_prototype)
            if watch.origin_prototype
            else None
        ),
        configuration=prototypes.configuration(session, watch),
        build_records=[
            BuildRecordRead.model_validate(b) for b in prototypes.list_build_records(session, watch)
        ],
        test_runs=[TestRunSummary.model_validate(r) for r in runs],
        latest_timing=testing.timing_summary(latest) if latest else None,
        latest_timing_run=TestRunSummary.model_validate(latest) if latest else None,
        experiments=related_experiments,
    )
