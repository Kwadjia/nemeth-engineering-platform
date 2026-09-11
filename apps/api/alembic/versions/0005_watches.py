"""Serialized watches; build records, part-instance location and test runs learn about them.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

WATCH_STATUSES = (
    "PLANNED",
    "IN_BUILD",
    "BUILT",
    "PERSONAL_PROTOTYPE",
    "DELIVERED",
    "IN_SERVICE",
    "RETIRED",
)


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
        "watches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("serial_number", sa.String(32), nullable=False),
        sa.Column("product_model_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *WATCH_STATUSES,
                name="watch_status",
                native_enum=False,
                length=24,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("owner_name", sa.String(200), nullable=True),
        sa.Column("origin_prototype_id", sa.Uuid(), nullable=True),
        sa.Column("assembled_on", sa.Date(), nullable=True),
        sa.Column("delivered_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["product_model_id"],
            ["product_models.id"],
            name=op.f("fk_watches_product_model_id_product_models"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["origin_prototype_id"],
            ["prototypes.id"],
            name=op.f("fk_watches_origin_prototype_id_prototypes"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_watches")),
    )
    op.create_index(op.f("ix_watches_identifier"), "watches", ["identifier"], unique=True)
    op.create_index(op.f("ix_watches_product_model_id"), "watches", ["product_model_id"])
    op.create_index(op.f("ix_watches_status"), "watches", ["status"])

    # --- part instances: where is it now (prototype xor watch) ------------------------
    op.add_column("part_instances", sa.Column("current_watch_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_part_instances_current_watch_id"), "part_instances", ["current_watch_id"]
    )
    op.create_foreign_key(
        op.f("fk_part_instances_current_watch_id_watches"),
        "part_instances",
        "watches",
        ["current_watch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "single_location",
        "part_instances",
        "NOT (current_prototype_id IS NOT NULL AND current_watch_id IS NOT NULL)",
    )

    # --- build records: exactly one unit --------------------------------------------
    op.add_column("build_records", sa.Column("watch_id", sa.Uuid(), nullable=True))
    op.alter_column("build_records", "prototype_id", existing_type=sa.Uuid(), nullable=True)
    op.create_index(op.f("ix_build_records_watch_id"), "build_records", ["watch_id"])
    op.create_foreign_key(
        op.f("fk_build_records_watch_id_watches"),
        "build_records",
        "watches",
        ["watch_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "single_unit",
        "build_records",
        "(CASE WHEN prototype_id IS NULL THEN 0 ELSE 1 END)"
        " + (CASE WHEN watch_id IS NULL THEN 0 ELSE 1 END) = 1",
    )

    # --- test runs: watches as subjects ---------------------------------------------
    op.add_column("test_runs", sa.Column("watch_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_test_runs_watch_id"), "test_runs", ["watch_id"])
    op.create_foreign_key(
        op.f("fk_test_runs_watch_id_watches"),
        "test_runs",
        "watches",
        ["watch_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(op.f("ck_test_runs_single_subject"), "test_runs", type_="check")
    op.create_check_constraint(
        "single_subject",
        "test_runs",
        "(CASE WHEN prototype_id IS NULL THEN 0 ELSE 1 END)"
        " + (CASE WHEN part_instance_id IS NULL THEN 0 ELSE 1 END)"
        " + (CASE WHEN component_revision_id IS NULL THEN 0 ELSE 1 END)"
        " + (CASE WHEN watch_id IS NULL THEN 0 ELSE 1 END) <= 1",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_test_runs_single_subject"), "test_runs", type_="check")
    op.create_check_constraint(
        "single_subject",
        "test_runs",
        "(CASE WHEN prototype_id IS NULL THEN 0 ELSE 1 END)"
        " + (CASE WHEN part_instance_id IS NULL THEN 0 ELSE 1 END)"
        " + (CASE WHEN component_revision_id IS NULL THEN 0 ELSE 1 END) <= 1",
    )
    op.drop_constraint(op.f("fk_test_runs_watch_id_watches"), "test_runs", type_="foreignkey")
    op.drop_index(op.f("ix_test_runs_watch_id"), table_name="test_runs")
    op.drop_column("test_runs", "watch_id")

    op.drop_constraint(op.f("ck_build_records_single_unit"), "build_records", type_="check")
    op.drop_constraint(
        op.f("fk_build_records_watch_id_watches"), "build_records", type_="foreignkey"
    )
    op.drop_index(op.f("ix_build_records_watch_id"), table_name="build_records")
    op.drop_column("build_records", "watch_id")
    op.alter_column("build_records", "prototype_id", existing_type=sa.Uuid(), nullable=False)

    op.drop_constraint(op.f("ck_part_instances_single_location"), "part_instances", type_="check")
    op.drop_constraint(
        op.f("fk_part_instances_current_watch_id_watches"), "part_instances", type_="foreignkey"
    )
    op.drop_index(op.f("ix_part_instances_current_watch_id"), table_name="part_instances")
    op.drop_column("part_instances", "current_watch_id")

    op.drop_table("watches")
