from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.db import get_session
from nemeth.core.errors import NotFoundError
from nemeth.modules.bom import service
from nemeth.modules.bom.schemas import (
    BomFlat,
    BomLineCreate,
    BomLineRead,
    BomLineUpdate,
    BomTree,
    ResolveMode,
    WhereUsedRow,
)
from nemeth.modules.components import service as components

router = APIRouter(tags=["bom"])


@router.get("/revisions/{revision_id}/bom", response_model=BomTree)
def get_bom_tree(
    revision_id: uuid.UUID,
    mode: ResolveMode = "latest",
    session: Session = Depends(get_session),
) -> BomTree:
    revision = components.get_revision(session, revision_id)
    return service.resolve_tree(session, revision, mode)


@router.get("/revisions/{revision_id}/bom/flat", response_model=BomFlat)
def get_bom_flat(
    revision_id: uuid.UUID,
    mode: ResolveMode = "latest",
    session: Session = Depends(get_session),
) -> BomFlat:
    revision = components.get_revision(session, revision_id)
    return service.flatten_tree(service.resolve_tree(session, revision, mode))


@router.get("/components/{ref}/bom", response_model=BomTree)
def get_component_bom(
    ref: str, mode: ResolveMode = "latest", session: Session = Depends(get_session)
) -> BomTree:
    """BOM of the component's latest revision."""
    component = components.get_component(session, ref)
    latest = component.latest_revision
    if latest is None:  # pragma: no cover
        raise NotFoundError(f"{component.identifier} has no revisions")
    return service.resolve_tree(session, components.get_revision(session, latest.id), mode)


@router.get("/components/{ref}/where-used", response_model=list[WhereUsedRow])
def get_where_used(ref: str, session: Session = Depends(get_session)) -> list[WhereUsedRow]:
    component = components.get_component(session, ref)
    return service.where_used(session, component)


@router.post(
    "/revisions/{revision_id}/bom-lines",
    response_model=BomLineRead,
    status_code=status.HTTP_201_CREATED,
)
def add_bom_line(
    revision_id: uuid.UUID,
    payload: BomLineCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> BomLineRead:
    revision = components.get_revision(session, revision_id)
    return BomLineRead.model_validate(service.add_line(session, actor, revision, payload))


@router.get("/bom-lines/{line_id}", response_model=BomLineRead)
def get_bom_line(line_id: uuid.UUID, session: Session = Depends(get_session)) -> BomLineRead:
    return BomLineRead.model_validate(service.get_line(session, line_id))


@router.patch("/bom-lines/{line_id}", response_model=BomLineRead)
def update_bom_line(
    line_id: uuid.UUID,
    payload: BomLineUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> BomLineRead:
    line = service.get_line(session, line_id)
    return BomLineRead.model_validate(service.update_line(session, actor, line, payload))


@router.delete("/bom-lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bom_line(
    line_id: uuid.UUID,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> Response:
    line = service.get_line(session, line_id)
    service.remove_line(session, actor, line)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
