from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.db import get_session
from nemeth.core.pagination import Page, PageParams, page_params
from nemeth.modules.changes import service
from nemeth.modules.changes.models import ChangeRole, ChangeStatus, EngineeringChange
from nemeth.modules.changes.schemas import (
    ChangeCreate,
    ChangeRead,
    ChangeSummary,
    ChangeUpdate,
    LinkRevisionRole,
)
from nemeth.modules.components import service as components
from nemeth.modules.components.schemas import ComponentSummary, RevisionSummary
from nemeth.modules.experiments.schemas import ExperimentSummary
from nemeth.modules.testing.schemas import TestRunSummary

router = APIRouter(tags=["changes"])


def _read(change: EngineeringChange) -> ChangeRead:
    return ChangeRead.model_validate(
        {
            **{
                k: getattr(change, k)
                for k in ChangeRead.model_fields
                if k not in ("revisions", "experiments", "test_runs")
            },
            "revisions": [
                {
                    "id": link.id,
                    "role": link.role,
                    "revision": RevisionSummary.model_validate(link.revision),
                    "component": ComponentSummary.model_validate(link.revision.component),
                }
                for link in change.revision_links
            ],
            "experiments": [
                ExperimentSummary.model_validate(link.experiment)
                for link in change.experiment_links
            ],
            "test_runs": [
                TestRunSummary.model_validate(link.test_run) for link in change.test_run_links
            ],
        }
    )


@router.get("/changes", response_model=Page[ChangeRead])
def list_changes(
    q: str | None = Query(default=None),
    status_filter: ChangeStatus | None = Query(default=None, alias="status"),
    open_only: bool = False,
    page: PageParams = Depends(page_params),
    session: Session = Depends(get_session),
) -> Page[ChangeRead]:
    items, total = service.list_changes(
        session, page, q=q, status=status_filter, open_only=open_only
    )
    return Page(items=[_read(c) for c in items], total=total, limit=page.limit, offset=page.offset)


@router.post("/changes", response_model=ChangeRead, status_code=status.HTTP_201_CREATED)
def create_change(
    payload: ChangeCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ChangeRead:
    return _read(service.create_change(session, actor, payload))


@router.get("/changes/{ref}", response_model=ChangeRead)
def get_change(ref: str, session: Session = Depends(get_session)) -> ChangeRead:
    return _read(service.get_change(session, ref))


@router.patch("/changes/{ref}", response_model=ChangeRead)
def update_change(
    ref: str,
    payload: ChangeUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ChangeRead:
    change = service.get_change(session, ref)
    return _read(service.update_change(session, actor, change, payload))


@router.post("/changes/{ref}/revisions", response_model=ChangeRead)
def link_revision(
    ref: str,
    payload: LinkRevisionRole,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ChangeRead:
    change = service.get_change(session, ref)
    return _read(
        service.link_revision(session, actor, change, payload.component_revision_id, payload.role)
    )


@router.delete("/changes/{ref}/revisions/{revision_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_revision(
    ref: str,
    revision_id: uuid.UUID,
    role: ChangeRole,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> Response:
    change = service.get_change(session, ref)
    service.unlink_revision(session, actor, change, revision_id, role)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/changes/{ref}/experiments/{experiment_ref}", response_model=ChangeRead)
def link_experiment(
    ref: str,
    experiment_ref: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ChangeRead:
    change = service.get_change(session, ref)
    return _read(service.link_experiment(session, actor, change, experiment_ref))


@router.delete(
    "/changes/{ref}/experiments/{experiment_ref}", status_code=status.HTTP_204_NO_CONTENT
)
def unlink_experiment(
    ref: str,
    experiment_ref: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> Response:
    change = service.get_change(session, ref)
    service.unlink_experiment(session, actor, change, experiment_ref)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/changes/{ref}/test-runs/{run_ref}", response_model=ChangeRead)
def link_test_run(
    ref: str,
    run_ref: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ChangeRead:
    change = service.get_change(session, ref)
    return _read(service.link_test_run(session, actor, change, run_ref))


@router.delete("/changes/{ref}/test-runs/{run_ref}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_test_run(
    ref: str,
    run_ref: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> Response:
    change = service.get_change(session, ref)
    service.unlink_test_run(session, actor, change, run_ref)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/revisions/{revision_id}/changes", response_model=list[ChangeSummary])
def revision_changes(
    revision_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[ChangeSummary]:
    """Changes in which this revision is affected or proposed: why it exists, or why it ended."""
    components.get_revision(session, revision_id)
    return [ChangeSummary.model_validate(c) for c in service.for_revision(session, revision_id)]
