"""Prototypes, part instances, build records and build entries (ADR-008).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

PROTOTYPE_STATUSES = ("PLANNED", "BUILDING", "ACTIVE", "RETIRED")
PART_SOURCES = ("IN_HOUSE", "PURCHASED", "SALVAGED", "OTHER")
PART_INSTANCE_STATUSES = ("AVAILABLE", "INSTALLED", "REMOVED", "SCRAPPED")
BUILD_ACTIONS = ("INSTALL", "REMOVE")


def _enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=16, create_constraint=True)


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_by", sa.String(64), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "prototypes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("status", _enum(PROTOTYPE_STATUSES, "prototype_status"), nullable=False),
        sa.Column("product_model_id", sa.Uuid(), nullable=True),
        sa.Column("caliber_id", sa.Uuid(), nullable=True),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("retired_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["product_model_id"],
            ["product_models.id"],
            name=op.f("fk_prototypes_product_model_id_product_models"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["caliber_id"],
            ["calibers.id"],
            name=op.f("fk_prototypes_caliber_id_calibers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prototypes")),
    )
    op.create_index(op.f("ix_prototypes_identifier"), "prototypes", ["identifier"], unique=True)
    op.create_index(op.f("ix_prototypes_status"), "prototypes", ["status"])

    op.create_table(
        "part_instances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("component_revision_id", sa.Uuid(), nullable=False),
        sa.Column("serial_number", sa.String(120), nullable=True),
        sa.Column("lot", sa.String(120), nullable=True),
        sa.Column("source", _enum(PART_SOURCES, "part_source"), nullable=False),
        sa.Column("status", _enum(PART_INSTANCE_STATUSES, "part_instance_status"), nullable=False),
        sa.Column("material_lot", sa.String(120), nullable=True),
        sa.Column("heat_treatment_lot", sa.String(120), nullable=True),
        sa.Column("supplier_note", sa.String(300), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        sa.Column("current_prototype_id", sa.Uuid(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["component_revision_id"],
            ["component_revisions.id"],
            name=op.f("fk_part_instances_component_revision_id_component_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["current_prototype_id"],
            ["prototypes.id"],
            name=op.f("fk_part_instances_current_prototype_id_prototypes"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_part_instances")),
    )
    op.create_index(
        op.f("ix_part_instances_identifier"), "part_instances", ["identifier"], unique=True
    )
    op.create_index(
        op.f("ix_part_instances_component_revision_id"), "part_instances", ["component_revision_id"]
    )
    op.create_index(op.f("ix_part_instances_status"), "part_instances", ["status"])
    op.create_index(
        op.f("ix_part_instances_current_prototype_id"), "part_instances", ["current_prototype_id"]
    )

    op.create_table(
        "build_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("prototype_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("performed_on", sa.Date(), nullable=False),
        sa.Column("performed_by", sa.String(120), nullable=False),
        sa.Column("procedure", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["prototype_id"],
            ["prototypes.id"],
            name=op.f("fk_build_records_prototype_id_prototypes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_build_records")),
    )
    op.create_index(
        op.f("ix_build_records_identifier"), "build_records", ["identifier"], unique=True
    )
    op.create_index(op.f("ix_build_records_prototype_id"), "build_records", ["prototype_id"])

    op.create_table(
        "build_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_record_id", sa.Uuid(), nullable=False),
        sa.Column("part_instance_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("action", _enum(BUILD_ACTIONS, "build_action"), nullable=False),
        sa.Column("position", sa.String(120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["build_record_id"],
            ["build_records.id"],
            name=op.f("fk_build_entries_build_record_id_build_records"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["part_instance_id"],
            ["part_instances.id"],
            name=op.f("fk_build_entries_part_instance_id_part_instances"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_build_entries")),
        sa.UniqueConstraint(
            "build_record_id", "sequence", name=op.f("uq_build_entries_build_record_id_sequence")
        ),
        sa.UniqueConstraint(
            "build_record_id",
            "part_instance_id",
            name=op.f("uq_build_entries_build_record_id_part_instance_id"),
        ),
    )
    op.create_index(op.f("ix_build_entries_build_record_id"), "build_entries", ["build_record_id"])
    op.create_index(
        op.f("ix_build_entries_part_instance_id"), "build_entries", ["part_instance_id"]
    )


def downgrade() -> None:
    op.drop_table("build_entries")
    op.drop_table("build_records")
    op.drop_table("part_instances")
    op.drop_table("prototypes")
