from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.db import get_session
from nemeth.core.pagination import Page, PageParams, page_params
from nemeth.modules.components import service as components
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.schemas import BuildRecordCreate, BuildRecordRead, UnitConfiguration
from nemeth.modules.watches import service
from nemeth.modules.watches.dossier import WatchDossier, build_dossier
from nemeth.modules.watches.models import Watch, WatchStatus
from nemeth.modules.watches.schemas import WatchCreate, WatchRead, WatchSummary, WatchUpdate

router = APIRouter(tags=["watches"])


def _read(watch: Watch) -> WatchRead:
    return WatchRead.model_validate(
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
    )


@router.get("/watches", response_model=Page[WatchRead])
def list_watches(
    status_filter: WatchStatus | None = Query(default=None, alias="status"),
    page: PageParams = Depends(page_params),
    session: Session = Depends(get_session),
) -> Page[WatchRead]:
    items, total = service.list_watches(session, page, status=status_filter)
    return Page(items=[_read(w) for w in items], total=total, limit=page.limit, offset=page.offset)


@router.post("/watches", response_model=WatchRead, status_code=status.HTTP_201_CREATED)
def create_watch(
    payload: WatchCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> WatchRead:
    return _read(service.create_watch(session, actor, payload))


@router.get("/watches/{ref}", response_model=WatchRead)
def get_watch(ref: str, session: Session = Depends(get_session)) -> WatchRead:
    return _read(service.get_watch(session, ref))


@router.patch("/watches/{ref}", response_model=WatchRead)
def update_watch(
    ref: str,
    payload: WatchUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> WatchRead:
    watch = service.get_watch(session, ref)
    return _read(service.update_watch(session, actor, watch, payload))


@router.get("/watches/{ref}/configuration", response_model=UnitConfiguration)
def get_configuration(ref: str, session: Session = Depends(get_session)) -> UnitConfiguration:
    return prototypes.configuration(session, service.get_watch(session, ref))


@router.get("/watches/{ref}/builds", response_model=list[BuildRecordRead])
def list_builds(ref: str, session: Session = Depends(get_session)) -> list[BuildRecordRead]:
    watch = service.get_watch(session, ref)
    return [
        BuildRecordRead.model_validate(b) for b in prototypes.list_build_records(session, watch)
    ]


@router.post(
    "/watches/{ref}/builds", response_model=BuildRecordRead, status_code=status.HTTP_201_CREATED
)
def create_build(
    ref: str,
    payload: BuildRecordCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> BuildRecordRead:
    watch = service.get_watch(session, ref)
    return BuildRecordRead.model_validate(
        prototypes.create_build_record(session, actor, watch, payload)
    )


@router.get("/watches/{ref}/dossier", response_model=WatchDossier)
def get_dossier(ref: str, session: Session = Depends(get_session)) -> WatchDossier:
    """The complete digital build record of one watch."""
    return build_dossier(session, service.get_watch(session, ref))


@router.get("/revisions/{revision_id}/watches", response_model=list[WatchSummary])
def revision_watches(
    revision_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[WatchSummary]:
    """Watches that currently contain a part made to this exact revision."""
    components.get_revision(session, revision_id)
    return [
        WatchSummary.model_validate(w)
        for w in prototypes.watches_containing_revision(session, revision_id)
    ]


@router.get("/models/{ref}/watches", response_model=list[WatchRead])
def model_watches(ref: str, session: Session = Depends(get_session)) -> list[WatchRead]:
    from nemeth.modules.products import service as products

    model = products.get_model(session, ref)
    return [_read(w) for w in service.by_model(session, model.id)]
