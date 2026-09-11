"""Attachments: file metadata linked to any entity; bytes live in FileStorage.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

KINDS = ("CAD", "DRAWING", "PHOTO", "TEST_RESULT", "MANUFACTURING", "CERTIFICATE", "OTHER")


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                *KINDS, name="attachment_kind", native_enum=False, length=16, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_key", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_by", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
        sa.UniqueConstraint("stored_key", name=op.f("uq_attachments_stored_key")),
    )
    op.create_index(op.f("ix_attachments_identifier"), "attachments", ["identifier"], unique=True)
    op.create_index(op.f("ix_attachments_kind"), "attachments", ["kind"])
    op.create_index(op.f("ix_attachments_sha256"), "attachments", ["sha256"])
    op.create_index("ix_attachments_entity", "attachments", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("attachments")
