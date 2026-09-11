from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.db import get_session
from nemeth.core.pagination import Page, PageParams, page_params
from nemeth.modules.components import service as components
from nemeth.modules.experiments import service
from nemeth.modules.experiments.models import Experiment, ExperimentStatus
from nemeth.modules.experiments.schemas import (
    ExperimentCreate,
    ExperimentRead,
    ExperimentSummary,
    ExperimentUpdate,
    LinkPrototype,
    LinkRevision,
)
from nemeth.modules.prototypes import service as prototypes

router = APIRouter(tags=["experiments"])


@router.get("/experiments", response_model=Page[ExperimentRead])
def list_experiments(
    q: str | None = Query(default=None),
    status_filter: ExperimentStatus | None = Query(default=None, alias="status"),
    prototype_id: uuid.UUID | None = None,
    page: PageParams = Depends(page_params),
    session: Session = Depends(get_session),
) -> Page[ExperimentRead]:
    items, total = service.list_experiments(
        session, page, q=q, status=status_filter, prototype_id=prototype_id
    )
    return Page(items=[_read(e) for e in items], total=total, limit=page.limit, offset=page.offset)


@router.post("/experiments", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
def create_experiment(
    payload: ExperimentCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ExperimentRead:
    return _read(service.create_experiment(session, actor, payload))


@router.get("/experiments/{ref}", response_model=ExperimentRead)
def get_experiment(ref: str, session: Session = Depends(get_session)) -> ExperimentRead:
    return _read(service.get_experiment(session, ref))


@router.patch("/experiments/{ref}", response_model=ExperimentRead)
def update_experiment(
    ref: str,
    payload: ExperimentUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ExperimentRead:
    experiment = service.get_experiment(session, ref)
    return _read(service.update_experiment(session, actor, experiment, payload))


@router.post("/experiments/{ref}/prototypes", response_model=ExperimentRead)
def link_prototype(
    ref: str,
    payload: LinkPrototype,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ExperimentRead:
    experiment = service.get_experiment(session, ref)
    return _read(service.link_prototype(session, actor, experiment, payload))


@router.delete(
    "/experiments/{ref}/prototypes/{prototype_ref}", status_code=status.HTTP_204_NO_CONTENT
)
def unlink_prototype(
    ref: str,
    prototype_ref: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> Response:
    experiment = service.get_experiment(session, ref)
    prototype = prototypes.get_prototype(session, prototype_ref)
    service.unlink_prototype(session, actor, experiment, prototype)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/experiments/{ref}/revisions", response_model=ExperimentRead)
def link_revision(
    ref: str,
    payload: LinkRevision,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ExperimentRead:
    experiment = service.get_experiment(session, ref)
    return _read(service.link_revision(session, actor, experiment, payload))


@router.delete("/experiments/{ref}/revisions/{revision_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_revision(
    ref: str,
    revision_id: uuid.UUID,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> Response:
    experiment = service.get_experiment(session, ref)
    service.unlink_revision(session, actor, experiment, revision_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/prototypes/{ref}/experiments", response_model=list[ExperimentSummary])
def prototype_experiments(
    ref: str, session: Session = Depends(get_session)
) -> list[ExperimentSummary]:
    prototype = prototypes.get_prototype(session, ref)
    items, _ = service.list_experiments(
        session, PageParams(limit=500, offset=0), prototype_id=prototype.id
    )
    return [ExperimentSummary.model_validate(e) for e in items]


@router.get("/revisions/{revision_id}/experiments", response_model=list[ExperimentSummary])
def revision_experiments(
    revision_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[ExperimentSummary]:
    components.get_revision(session, revision_id)
    return [ExperimentSummary.model_validate(e) for e in service.for_revision(session, revision_id)]


def _read(experiment: Experiment) -> ExperimentRead:
    base = ExperimentRead.model_validate(
        {
            **{
                k: getattr(experiment, k)
                for k in ExperimentRead.model_fields
                if k not in ("prototypes", "revisions")
            },
            "prototypes": [
                {"id": link.id, "role": link.role, "prototype": link.prototype}
                for link in experiment.prototype_links
            ],
            "revisions": [
                {
                    "id": link.id,
                    "role": link.role,
                    "revision": link.revision,
                    "component": link.revision.component,
                }
                for link in experiment.revision_links
            ],
        }
    )
    return base
