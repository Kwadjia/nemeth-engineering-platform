from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from nemeth.modules.components.schemas import AuditFields
from nemeth.modules.documents.models import AttachmentKind

EntityType = Literal[
    "product",
    "product_model",
    "caliber",
    "component",
    "component_revision",
    "prototype",
    "part_instance",
    "build_record",
    "experiment",
    "test_run",
    "watch",
]

ENTITY_TYPES: tuple[str, ...] = (
    "product",
    "product_model",
    "caliber",
    "component",
    "component_revision",
    "prototype",
    "part_instance",
    "build_record",
    "experiment",
    "test_run",
    "watch",
)


class EntityRef(BaseModel):
    entity_type: EntityType
    entity_id: uuid.UUID
    identifier: str
    label: str


class AttachmentRead(AuditFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    entity_type: EntityType
    entity_id: uuid.UUID
    kind: AttachmentKind
    original_filename: str
    stored_key: str
    sha256: str
    mime_type: str
    size_bytes: int
    description: str | None


class AttachmentWithEntity(AttachmentRead):
    entity: EntityRef | None


class AttachmentUpdate(BaseModel):
    kind: AttachmentKind | None = None
    description: str | None = Field(default=None, max_length=2000)


class UploadPolicy(BaseModel):
    max_bytes: int
    allowed_extensions: list[str]
    kinds: list[AttachmentKind]
    entity_types: list[str]
