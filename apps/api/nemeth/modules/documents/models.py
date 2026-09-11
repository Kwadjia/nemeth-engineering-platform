from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import BigInteger, Enum, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from nemeth.core.db import AuditMixin, Base, UUIDPrimaryKeyMixin


class AttachmentKind(StrEnum):
    CAD = "CAD"
    DRAWING = "DRAWING"
    PHOTO = "PHOTO"
    TEST_RESULT = "TEST_RESULT"
    MANUFACTURING = "MANUFACTURING"
    CERTIFICATE = "CERTIFICATE"
    OTHER = "OTHER"


#: Storage folder per kind (see storage/README.md).
STORAGE_CATEGORY: dict[AttachmentKind, str] = {
    AttachmentKind.CAD: "cad",
    AttachmentKind.DRAWING: "drawings",
    AttachmentKind.PHOTO: "photos",
    AttachmentKind.TEST_RESULT: "test-results",
    AttachmentKind.MANUFACTURING: "manufacturing",
    AttachmentKind.CERTIFICATE: "certificates",
    AttachmentKind.OTHER: "other",
}


class Attachment(UUIDPrimaryKeyMixin, AuditMixin, Base):
    """File metadata. The bytes live in FileStorage under ``stored_key``."""

    __tablename__ = "attachments"
    __table_args__ = (Index("ix_attachments_entity", "entity_type", "entity_id"),)

    identifier: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[AttachmentKind] = mapped_column(
        Enum(
            AttachmentKind,
            name="attachment_kind",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<Attachment {self.identifier} {self.original_filename}>"
