"""Test types, test runs and measurements.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

OUTCOMES = ("PASS", "FAIL", "INFO")


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
        "test_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("allow_custom_metrics", sa.Boolean(), nullable=False),
        sa.Column("uses_positions", sa.Boolean(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_test_types")),
    )
    op.create_index(op.f("ix_test_types_code"), "test_types", ["code"], unique=True)

    op.create_table(
        "test_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("test_type_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("prototype_id", sa.Uuid(), nullable=True),
        sa.Column("part_instance_id", sa.Uuid(), nullable=True),
        sa.Column("component_revision_id", sa.Uuid(), nullable=True),
        sa.Column("experiment_id", sa.Uuid(), nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("performed_by", sa.String(120), nullable=False),
        sa.Column("equipment", sa.String(200), nullable=True),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "outcome",
            sa.Enum(
                *OUTCOMES, name="test_outcome", native_enum=False, length=8, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.CheckConstraint(
            "(CASE WHEN prototype_id IS NULL THEN 0 ELSE 1 END)"
            " + (CASE WHEN part_instance_id IS NULL THEN 0 ELSE 1 END)"
            " + (CASE WHEN component_revision_id IS NULL THEN 0 ELSE 1 END) <= 1",
            name=op.f("ck_test_runs_single_subject"),
        ),
        sa.ForeignKeyConstraint(
            ["test_type_id"],
            ["test_types.id"],
            name=op.f("fk_test_runs_test_type_id_test_types"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prototype_id"],
            ["prototypes.id"],
            name=op.f("fk_test_runs_prototype_id_prototypes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["part_instance_id"],
            ["part_instances.id"],
            name=op.f("fk_test_runs_part_instance_id_part_instances"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["component_revision_id"],
            ["component_revisions.id"],
            name=op.f("fk_test_runs_component_revision_id_component_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.id"],
            name=op.f("fk_test_runs_experiment_id_experiments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_test_runs")),
    )
    op.create_index(op.f("ix_test_runs_identifier"), "test_runs", ["identifier"], unique=True)
    for column in (
        "test_type_id",
        "prototype_id",
        "part_instance_id",
        "component_revision_id",
        "experiment_id",
        "performed_at",
    ):
        op.create_index(op.f(f"ix_test_runs_{column}"), "test_runs", [column])

    op.create_table(
        "measurements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("test_run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit", sa.String(16), nullable=True),
        sa.Column("position", sa.String(8), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["test_run_id"],
            ["test_runs.id"],
            name=op.f("fk_measurements_test_run_id_test_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measurements")),
        sa.UniqueConstraint(
            "test_run_id", "sequence", name=op.f("uq_measurements_test_run_id_sequence")
        ),
    )
    op.create_index(op.f("ix_measurements_test_run_id"), "measurements", ["test_run_id"])
    op.create_index(op.f("ix_measurements_metric"), "measurements", ["metric"])
    op.create_index(op.f("ix_measurements_position"), "measurements", ["position"])


def downgrade() -> None:
    op.drop_table("measurements")
    op.drop_table("test_runs")
    op.drop_table("test_types")
