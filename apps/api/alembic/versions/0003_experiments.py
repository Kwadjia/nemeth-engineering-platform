"""Experiments and their links to prototypes and component revisions.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

STATUSES = ("PLANNED", "IN_PROGRESS", "COMPLETED", "ABANDONED")
OUTCOMES = ("IMPROVEMENT", "NO_CHANGE", "REGRESSION", "INCONCLUSIVE")


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
        "experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", _enum(STATUSES, "experiment_status"), nullable=False),
        sa.Column("outcome", _enum(OUTCOMES, "experiment_outcome"), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("configuration", sa.Text(), nullable=True),
        sa.Column("methodology", sa.Text(), nullable=True),
        sa.Column("equipment", sa.Text(), nullable=True),
        sa.Column("procedure", sa.Text(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("follow_up", sa.Text(), nullable=True),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("completed_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_experiments")),
    )
    op.create_index(op.f("ix_experiments_identifier"), "experiments", ["identifier"], unique=True)
    op.create_index(op.f("ix_experiments_status"), "experiments", ["status"])

    op.create_table(
        "experiment_prototypes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("prototype_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(80), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.id"],
            name=op.f("fk_experiment_prototypes_experiment_id_experiments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prototype_id"],
            ["prototypes.id"],
            name=op.f("fk_experiment_prototypes_prototype_id_prototypes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_experiment_prototypes")),
        sa.UniqueConstraint(
            "experiment_id",
            "prototype_id",
            name=op.f("uq_experiment_prototypes_experiment_id_prototype_id"),
        ),
    )
    op.create_index(
        op.f("ix_experiment_prototypes_experiment_id"), "experiment_prototypes", ["experiment_id"]
    )
    op.create_index(
        op.f("ix_experiment_prototypes_prototype_id"), "experiment_prototypes", ["prototype_id"]
    )

    op.create_table(
        "experiment_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("component_revision_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(80), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.id"],
            name=op.f("fk_experiment_revisions_experiment_id_experiments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["component_revision_id"],
            ["component_revisions.id"],
            name=op.f("fk_experiment_revisions_component_revision_id_component_revisions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_experiment_revisions")),
        sa.UniqueConstraint(
            "experiment_id",
            "component_revision_id",
            name=op.f("uq_experiment_revisions_experiment_id_component_revision_id"),
        ),
    )
    op.create_index(
        op.f("ix_experiment_revisions_experiment_id"), "experiment_revisions", ["experiment_id"]
    )
    op.create_index(
        op.f("ix_experiment_revisions_component_revision_id"),
        "experiment_revisions",
        ["component_revision_id"],
    )


def downgrade() -> None:
    op.drop_table("experiment_revisions")
    op.drop_table("experiment_prototypes")
    op.drop_table("experiments")
