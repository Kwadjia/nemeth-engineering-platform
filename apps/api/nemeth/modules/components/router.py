from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.db import get_session
from nemeth.core.lifecycle import LifecycleState
from nemeth.core.pagination import Page, PageParams, page_params
from nemeth.modules.components import service
from nemeth.modules.components.models import ComponentFamily, ComponentKind
from nemeth.modules.components.schemas import (
    ComponentCreate,
    ComponentDetail,
    ComponentRead,
    ComponentUpdate,
    RevisionCreate,
    RevisionRead,
    RevisionUpdate,
    TransitionRequest,
)

router = APIRouter(tags=["components"])


@router.get("/components", response_model=Page[ComponentRead])
def list_components(
    q: str | None = Query(default=None, description="Search identifier or name"),
    family: ComponentFamily | None = None,
    kind: ComponentKind | None = None,
    state: LifecycleState | None = Query(default=None, description="State of the latest revision"),
    placeholder: bool | None = None,
    page: PageParams = Depends(page_params),
    session: Session = Depends(get_session),
) -> Page[ComponentRead]:
    items, total = service.list_components(
        session, page=page, q=q, family=family, kind=kind, state=state, placeholder=placeholder
    )
    return Page(
        items=[ComponentRead.model_validate(c) for c in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("/components", response_model=ComponentDetail, status_code=status.HTTP_201_CREATED)
def create_component(
    payload: ComponentCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ComponentDetail:
    component = service.create_component(session, actor, payload)
    return ComponentDetail.model_validate(component)


@router.get("/components/{ref}", response_model=ComponentDetail)
def get_component(ref: str, session: Session = Depends(get_session)) -> ComponentDetail:
    return ComponentDetail.model_validate(service.get_component(session, ref))


@router.patch("/components/{ref}", response_model=ComponentDetail)
def update_component(
    ref: str,
    payload: ComponentUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ComponentDetail:
    component = service.get_component(session, ref)
    return ComponentDetail.model_validate(
        service.update_component(session, actor, component, payload)
    )


@router.get("/components/{ref}/revisions", response_model=list[RevisionRead])
def list_revisions(ref: str, session: Session = Depends(get_session)) -> list[RevisionRead]:
    component = service.get_component(session, ref)
    return [RevisionRead.model_validate(r) for r in component.revisions]


@router.post(
    "/components/{ref}/revisions", response_model=RevisionRead, status_code=status.HTTP_201_CREATED
)
def create_revision(
    ref: str,
    payload: RevisionCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> RevisionRead:
    component = service.get_component(session, ref)
    revision = service.create_revision(session, actor, component, payload)
    return RevisionRead.model_validate(service.get_revision(session, revision.id))


@router.get("/components/{ref}/revisions/{label}", response_model=RevisionRead)
def get_revision_by_label(
    ref: str, label: str, session: Session = Depends(get_session)
) -> RevisionRead:
    component = service.get_component(session, ref)
    return RevisionRead.model_validate(service.get_revision_by_label(session, component, label))


@router.get("/revisions/{revision_id}", response_model=RevisionRead)
def get_revision(revision_id: uuid.UUID, session: Session = Depends(get_session)) -> RevisionRead:
    return RevisionRead.model_validate(service.get_revision(session, revision_id))


@router.patch("/revisions/{revision_id}", response_model=RevisionRead)
def update_revision(
    revision_id: uuid.UUID,
    payload: RevisionUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> RevisionRead:
    revision = service.get_revision(session, revision_id)
    return RevisionRead.model_validate(service.update_revision(session, actor, revision, payload))


@router.post("/revisions/{revision_id}/transition", response_model=RevisionRead)
def transition_revision(
    revision_id: uuid.UUID,
    payload: TransitionRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> RevisionRead:
    revision = service.get_revision(session, revision_id)
    return RevisionRead.model_validate(
        service.transition_revision(session, actor, revision, payload.target_state)
    )
