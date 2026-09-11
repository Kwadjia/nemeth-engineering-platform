"""Attachment rules: validation, hashing, storage, duplicate detection, entity resolution."""

from __future__ import annotations

import mimetypes
import uuid
from collections.abc import Iterator
from functools import lru_cache
from pathlib import PurePosixPath
from typing import Any, BinaryIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nemeth.core.audit import stamp_created, stamp_updated
from nemeth.core.auth import Actor
from nemeth.core.config import Settings, get_settings
from nemeth.core.errors import ConflictError, DomainValidationError, NotFoundError
from nemeth.core.identifiers import next_identifier
from nemeth.core.lookup import get_by_ref
from nemeth.core.pagination import PageParams
from nemeth.core.storage import FileStorage, build_storage, make_key
from nemeth.modules.components.models import Component, ComponentRevision
from nemeth.modules.documents.models import STORAGE_CATEGORY, Attachment, AttachmentKind
from nemeth.modules.documents.schemas import ENTITY_TYPES, AttachmentUpdate, EntityRef
from nemeth.modules.experiments.models import Experiment
from nemeth.modules.products.models import Caliber, Product, ProductModel
from nemeth.modules.prototypes.models import BuildRecord, PartInstance, Prototype
from nemeth.modules.testing.models import TestRun
from nemeth.modules.watches.models import Watch

#: Extensions accepted for upload. Case-insensitive; the list is deliberately explicit.
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".step", ".stp", ".iges", ".igs", ".stl", ".3mf", ".f3d", ".fcstd", ".x_t",
        ".dxf", ".dwg", ".svg", ".pdf",
        ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp", ".gif",
        ".csv", ".json", ".txt", ".md", ".xlsx", ".ods",
        ".mp4", ".mov",
        ".zip",
    }
)  # fmt: skip

_ENTITY_MODELS: dict[str, type[Any]] = {
    "product": Product,
    "product_model": ProductModel,
    "caliber": Caliber,
    "component": Component,
    "component_revision": ComponentRevision,
    "prototype": Prototype,
    "part_instance": PartInstance,
    "build_record": BuildRecord,
    "experiment": Experiment,
    "test_run": TestRun,
    "watch": Watch,
}


@lru_cache
def get_storage() -> FileStorage:
    return build_storage(get_settings())


def _entity_label(entity_type: str, entity: Any) -> tuple[str, str]:
    if entity_type == "component_revision":
        return entity.display_identifier, entity.component.name
    identifier = getattr(entity, "identifier", str(entity.id))
    label = getattr(entity, "name", None) or getattr(entity, "title", None) or identifier
    return identifier, str(label)


def resolve_entity(session: Session, entity_type: str, entity_id: uuid.UUID) -> EntityRef:
    model = _ENTITY_MODELS.get(entity_type)
    if model is None:
        raise DomainValidationError(
            f"Unknown entity type {entity_type!r}. Known: {', '.join(ENTITY_TYPES)}",
            field="entity_type",
        )
    entity = session.get(model, entity_id)
    if entity is None:
        raise NotFoundError(f"{entity_type} {entity_id} not found", resource=entity_type)
    identifier, label = _entity_label(entity_type, entity)
    return EntityRef(
        entity_type=entity_type, entity_id=entity_id, identifier=identifier, label=label
    )


def entity_ref_or_none(session: Session, attachment: Attachment) -> EntityRef | None:
    try:
        return resolve_entity(session, attachment.entity_type, attachment.entity_id)
    except (NotFoundError, DomainValidationError):
        return None


def _exists(session: Session, identifier: str) -> bool:
    stmt = select(func.count()).select_from(Attachment).where(Attachment.identifier == identifier)
    return bool(session.execute(stmt).scalar_one())


def get_attachment(session: Session, ref: str) -> Attachment:
    return get_by_ref(session, Attachment, ref, label="Attachment")


def list_attachments(
    session: Session,
    page: PageParams,
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    kind: AttachmentKind | None = None,
    q: str | None = None,
) -> tuple[list[Attachment], int]:
    stmt = select(Attachment)
    if entity_type is not None:
        stmt = stmt.where(Attachment.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(Attachment.entity_id == entity_id)
    if kind is not None:
        stmt = stmt.where(Attachment.kind == kind)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            Attachment.original_filename.ilike(pattern)
            | Attachment.identifier.ilike(pattern)
            | Attachment.description.ilike(pattern)
        )
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = stmt.order_by(Attachment.created_at.desc()).limit(page.limit).offset(page.offset)
    return list(session.execute(stmt).scalars()), int(total)


def validate_filename(filename: str) -> str:
    """Return a clean base name; reject empty names and disallowed extensions."""
    name = PurePosixPath(filename.replace("\\", "/")).name.strip()
    if not name or name in (".", ".."):
        raise DomainValidationError("A filename is required", field="file")
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise DomainValidationError(
            f"File type {suffix or '(none)'} is not accepted. Allowed: {allowed}",
            field="file",
            extension=suffix,
        )
    return name[:255]


def _mime_for(name: str, declared: str | None) -> str:
    guessed, _ = mimetypes.guess_type(name)
    if guessed:
        return guessed
    if declared and "/" in declared and len(declared) <= 127:
        return declared
    return "application/octet-stream"


def upload_attachment(
    session: Session,
    actor: Actor,
    storage: FileStorage,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    kind: AttachmentKind,
    filename: str,
    stream: BinaryIO,
    declared_mime: str | None,
    description: str | None,
    settings: Settings | None = None,
) -> Attachment:
    settings = settings or get_settings()
    resolve_entity(session, entity_type, entity_id)
    name = validate_filename(filename)
    key = make_key(STORAGE_CATEGORY[kind], name)

    stored = storage.put(key, stream)
    try:
        if stored.size == 0:
            raise DomainValidationError("The file is empty", field="file")
        if stored.size > settings.upload_max_bytes:
            raise DomainValidationError(
                f"The file is {stored.size} bytes; the limit is {settings.upload_max_bytes} bytes",
                field="file",
            )
        duplicate = session.execute(
            select(Attachment).where(
                Attachment.entity_type == entity_type,
                Attachment.entity_id == entity_id,
                Attachment.sha256 == stored.sha256,
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise ConflictError(
                f"An identical file is already attached as {duplicate.identifier} "
                f"({duplicate.original_filename}); the content has not changed.",
                existing_identifier=duplicate.identifier,
                sha256=stored.sha256,
            )
    except Exception:
        storage.delete(key)
        raise

    attachment = Attachment(
        identifier=next_identifier(session, "DOC", exists=lambda c: _exists(session, c), width=5),
        entity_type=entity_type,
        entity_id=entity_id,
        kind=kind,
        original_filename=name,
        stored_key=stored.key,
        sha256=stored.sha256,
        mime_type=_mime_for(name, declared_mime),
        size_bytes=stored.size,
        description=description,
    )
    stamp_created(attachment, actor)
    session.add(attachment)
    session.flush()
    return attachment


def update_attachment(
    session: Session, actor: Actor, attachment: Attachment, data: AttachmentUpdate
) -> Attachment:
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "kind" and value is None:
            continue
        setattr(attachment, field, value)
    stamp_updated(attachment, actor)
    session.flush()
    return attachment


def delete_attachment(session: Session, storage: FileStorage, attachment: Attachment) -> None:
    key = attachment.stored_key
    session.delete(attachment)
    session.flush()
    storage.delete(key)


def open_content(storage: FileStorage, attachment: Attachment) -> Iterator[bytes]:
    with storage.open(attachment.stored_key) as fh:
        while chunk := fh.read(1024 * 1024):
            yield chunk


def count_by_kind(session: Session) -> dict[str, int]:
    stmt = select(Attachment.kind, func.count()).group_by(Attachment.kind)
    counts = {k.value: 0 for k in AttachmentKind}
    for kind, count in session.execute(stmt).all():
        counts[AttachmentKind(kind).value] = int(count)
    return counts
