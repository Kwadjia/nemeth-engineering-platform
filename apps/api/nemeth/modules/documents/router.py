from __future__ import annotations

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.config import Settings, get_settings
from nemeth.core.db import get_session
from nemeth.core.pagination import Page, PageParams, page_params
from nemeth.core.storage import FileStorage
from nemeth.modules.documents import service
from nemeth.modules.documents.models import Attachment, AttachmentKind
from nemeth.modules.documents.schemas import (
    ENTITY_TYPES,
    AttachmentRead,
    AttachmentUpdate,
    AttachmentWithEntity,
    EntityType,
    UploadPolicy,
)

router = APIRouter(tags=["documents"])


def _with_entity(session: Session, attachment: Attachment) -> AttachmentWithEntity:
    return AttachmentWithEntity.model_validate(
        {
            **{k: getattr(attachment, k) for k in AttachmentRead.model_fields},
            "entity": service.entity_ref_or_none(session, attachment),
        }
    )


@router.get("/attachments/policy", response_model=UploadPolicy)
def upload_policy(settings: Settings = Depends(get_settings)) -> UploadPolicy:
    return UploadPolicy(
        max_bytes=settings.upload_max_bytes,
        allowed_extensions=sorted(service.ALLOWED_EXTENSIONS),
        kinds=list(AttachmentKind),
        entity_types=list(ENTITY_TYPES),
    )


@router.get("/attachments", response_model=Page[AttachmentWithEntity])
def list_attachments(
    entity_type: EntityType | None = None,
    entity_id: uuid.UUID | None = None,
    kind: AttachmentKind | None = None,
    q: str | None = Query(default=None),
    page: PageParams = Depends(page_params),
    session: Session = Depends(get_session),
) -> Page[AttachmentWithEntity]:
    items, total = service.list_attachments(
        session, page, entity_type=entity_type, entity_id=entity_id, kind=kind, q=q
    )
    return Page(
        items=[_with_entity(session, a) for a in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def upload_attachment(
    file: UploadFile = File(...),
    entity_type: EntityType = Form(...),
    entity_id: uuid.UUID = Form(...),
    kind: AttachmentKind = Form(default=AttachmentKind.OTHER),
    description: str | None = Form(default=None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
    storage: FileStorage = Depends(service.get_storage),
    settings: Settings = Depends(get_settings),
) -> AttachmentRead:
    attachment = service.upload_attachment(
        session,
        actor,
        storage,
        entity_type=entity_type,
        entity_id=entity_id,
        kind=kind,
        filename=file.filename or "",
        stream=file.file,
        declared_mime=file.content_type,
        description=description,
        settings=settings,
    )
    return AttachmentRead.model_validate(attachment)


@router.get("/attachments/{ref}", response_model=AttachmentWithEntity)
def get_attachment(ref: str, session: Session = Depends(get_session)) -> AttachmentWithEntity:
    return _with_entity(session, service.get_attachment(session, ref))


@router.get("/attachments/{ref}/content")
def download_attachment(
    ref: str,
    inline: bool = False,
    session: Session = Depends(get_session),
    storage: FileStorage = Depends(service.get_storage),
) -> StreamingResponse:
    attachment = service.get_attachment(session, ref)
    disposition = "inline" if inline else "attachment"
    filename = quote(attachment.original_filename)
    return StreamingResponse(
        service.open_content(storage, attachment),
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{filename}",
            "Content-Length": str(attachment.size_bytes),
            "X-Content-SHA256": attachment.sha256,
        },
    )


@router.patch("/attachments/{ref}", response_model=AttachmentWithEntity)
def update_attachment(
    ref: str,
    payload: AttachmentUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> AttachmentWithEntity:
    attachment = service.get_attachment(session, ref)
    return _with_entity(session, service.update_attachment(session, actor, attachment, payload))


@router.delete("/attachments/{ref}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    ref: str,
    session: Session = Depends(get_session),
    storage: FileStorage = Depends(service.get_storage),
) -> Response:
    attachment = service.get_attachment(session, ref)
    service.delete_attachment(session, storage, attachment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
