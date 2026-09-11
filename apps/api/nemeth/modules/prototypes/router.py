from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.db import get_session
from nemeth.core.pagination import Page, PageParams, page_params
from nemeth.modules.components import service as components
from nemeth.modules.prototypes import service
from nemeth.modules.prototypes.models import PartInstanceStatus, PrototypeStatus
from nemeth.modules.prototypes.schemas import (
    BuildRecordCreate,
    BuildRecordRead,
    BuildRecordUpdate,
    PartInstanceCreate,
    PartInstanceRead,
    PartInstanceUpdate,
    PrototypeConfiguration,
    PrototypeCreate,
    PrototypeRead,
    PrototypeSummary,
    PrototypeUpdate,
)

router = APIRouter(tags=["prototypes"])


# --- prototypes --------------------------------------------------------------------


@router.get("/prototypes", response_model=Page[PrototypeRead])
def list_prototypes(
    status_filter: PrototypeStatus | None = Query(default=None, alias="status"),
    page: PageParams = Depends(page_params),
    session: Session = Depends(get_session),
) -> Page[PrototypeRead]:
    items, total = service.list_prototypes(session, page, status_filter)
    return Page(
        items=[PrototypeRead.model_validate(p) for p in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("/prototypes", response_model=PrototypeRead, status_code=status.HTTP_201_CREATED)
def create_prototype(
    payload: PrototypeCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> PrototypeRead:
    return PrototypeRead.model_validate(service.create_prototype(session, actor, payload))


@router.get("/prototypes/{ref}", response_model=PrototypeRead)
def get_prototype(ref: str, session: Session = Depends(get_session)) -> PrototypeRead:
    return PrototypeRead.model_validate(service.get_prototype(session, ref))


@router.patch("/prototypes/{ref}", response_model=PrototypeRead)
def update_prototype(
    ref: str,
    payload: PrototypeUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> PrototypeRead:
    prototype = service.get_prototype(session, ref)
    return PrototypeRead.model_validate(
        service.update_prototype(session, actor, prototype, payload)
    )


@router.get("/prototypes/{ref}/configuration", response_model=PrototypeConfiguration)
def get_configuration(ref: str, session: Session = Depends(get_session)) -> PrototypeConfiguration:
    return service.configuration(session, service.get_prototype(session, ref))


@router.get("/prototypes/{ref}/builds", response_model=list[BuildRecordRead])
def list_builds(ref: str, session: Session = Depends(get_session)) -> list[BuildRecordRead]:
    prototype = service.get_prototype(session, ref)
    return [
        BuildRecordRead.model_validate(b) for b in service.list_build_records(session, prototype)
    ]


@router.post(
    "/prototypes/{ref}/builds", response_model=BuildRecordRead, status_code=status.HTTP_201_CREATED
)
def create_build(
    ref: str,
    payload: BuildRecordCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> BuildRecordRead:
    prototype = service.get_prototype(session, ref)
    return BuildRecordRead.model_validate(
        service.create_build_record(session, actor, prototype, payload)
    )


@router.get("/builds/{ref}", response_model=BuildRecordRead)
def get_build(ref: str, session: Session = Depends(get_session)) -> BuildRecordRead:
    return BuildRecordRead.model_validate(service.get_build_record(session, ref))


@router.patch("/builds/{ref}", response_model=BuildRecordRead)
def update_build(
    ref: str,
    payload: BuildRecordUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> BuildRecordRead:
    record = service.get_build_record(session, ref)
    return BuildRecordRead.model_validate(
        service.update_build_record(session, actor, record, payload)
    )


# --- part instances ----------------------------------------------------------------


@router.get("/part-instances", response_model=Page[PartInstanceRead])
def list_part_instances(
    q: str | None = Query(default=None, description="Search instance, serial, component"),
    status_filter: PartInstanceStatus | None = Query(default=None, alias="status"),
    component_id: uuid.UUID | None = None,
    prototype_id: uuid.UUID | None = None,
    page: PageParams = Depends(page_params),
    session: Session = Depends(get_session),
) -> Page[PartInstanceRead]:
    items, total = service.list_part_instances(
        session,
        page,
        q=q,
        status=status_filter,
        component_id=component_id,
        prototype_id=prototype_id,
    )
    return Page(
        items=[PartInstanceRead.model_validate(i) for i in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "/part-instances", response_model=list[PartInstanceRead], status_code=status.HTTP_201_CREATED
)
def create_part_instances(
    payload: PartInstanceCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> list[PartInstanceRead]:
    return [
        PartInstanceRead.model_validate(i)
        for i in service.create_part_instances(session, actor, payload)
    ]


@router.get("/part-instances/{ref}", response_model=PartInstanceRead)
def get_part_instance(ref: str, session: Session = Depends(get_session)) -> PartInstanceRead:
    return PartInstanceRead.model_validate(service.get_part_instance(session, ref))


@router.patch("/part-instances/{ref}", response_model=PartInstanceRead)
def update_part_instance(
    ref: str,
    payload: PartInstanceUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> PartInstanceRead:
    instance = service.get_part_instance(session, ref)
    return PartInstanceRead.model_validate(
        service.update_part_instance(session, actor, instance, payload)
    )


@router.get("/components/{ref}/part-instances", response_model=list[PartInstanceRead])
def component_part_instances(
    ref: str, session: Session = Depends(get_session)
) -> list[PartInstanceRead]:
    component = components.get_component(session, ref)
    return [
        PartInstanceRead.model_validate(i)
        for i in service.instances_for_component(session, component)
    ]


@router.get("/revisions/{revision_id}/prototypes", response_model=list[PrototypeSummary])
def revision_prototypes(
    revision_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[PrototypeSummary]:
    """Prototypes that currently contain a part made to this exact revision."""
    components.get_revision(session, revision_id)
    return [
        PrototypeSummary.model_validate(p)
        for p in service.prototypes_containing_revision(session, revision_id)
    ]
