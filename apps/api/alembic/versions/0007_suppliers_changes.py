"""Suppliers (linked from revisions and part instances) and engineering changes.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

SUPPLIER_KINDS = (
    "MACHINE_SHOP",
    "MATERIAL",
    "PLATING",
    "HEAT_TREATMENT",
    "COMPONENTS",
    "TOOLING",
    "IN_HOUSE",
    "OTHER",
)
CHANGE_STATUSES = ("DRAFT", "PROPOSED", "APPROVED", "IMPLEMENTED", "REJECTED")
CHANGE_ROLES = ("AFFECTED", "PROPOSED")


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


def _link_table(name: str, column: str, target: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_id", sa.Uuid(), nullable=False),
        sa.Column(column, sa.Uuid(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["change_id"],
            ["engineering_changes.id"],
            name=op.f(f"fk_{name}_change_id_engineering_changes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            [column],
            [f"{target}.id"],
            name=op.f(f"fk_{name}_{column}_{target}"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{name}")),
        sa.UniqueConstraint("change_id", column, name=op.f(f"uq_{name}_change_id_{column}")),
    )
    op.create_index(op.f(f"ix_{name}_change_id"), name, ["change_id"])
    op.create_index(op.f(f"ix_{name}_{column}"), name, [column])


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", _enum(SUPPLIER_KINDS, "supplier_kind"), nullable=False),
        sa.Column("capabilities", sa.Text(), nullable=True),
        sa.Column("contact_name", sa.String(200), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(60), nullable=True),
        sa.Column("website", sa.String(300), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("country", sa.String(80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
    )
    op.create_index(op.f("ix_suppliers_identifier"), "suppliers", ["identifier"], unique=True)
    op.create_index(op.f("ix_suppliers_kind"), "suppliers", ["kind"])

    for table in ("component_revisions", "part_instances"):
        op.add_column(table, sa.Column("supplier_id", sa.Uuid(), nullable=True))
        op.create_index(op.f(f"ix_{table}_supplier_id"), table, ["supplier_id"])
        op.create_foreign_key(
            op.f(f"fk_{table}_supplier_id_suppliers"),
            table,
            "suppliers",
            ["supplier_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_table(
        "engineering_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", _enum(CHANGE_STATUSES, "change_status"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.String(120), nullable=False),
        sa.Column("approved_by", sa.String(120), nullable=True),
        sa.Column("approved_on", sa.Date(), nullable=True),
        sa.Column("implemented_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_engineering_changes")),
    )
    op.create_index(
        op.f("ix_engineering_changes_identifier"),
        "engineering_changes",
        ["identifier"],
        unique=True,
    )
    op.create_index(op.f("ix_engineering_changes_status"), "engineering_changes", ["status"])

    op.create_table(
        "change_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_id", sa.Uuid(), nullable=False),
        sa.Column("component_revision_id", sa.Uuid(), nullable=False),
        sa.Column("role", _enum(CHANGE_ROLES, "change_role"), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["change_id"],
            ["engineering_changes.id"],
            name=op.f("fk_change_revisions_change_id_engineering_changes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["component_revision_id"],
            ["component_revisions.id"],
            name=op.f("fk_change_revisions_component_revision_id_component_revisions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_change_revisions")),
        sa.UniqueConstraint(
            "change_id",
            "component_revision_id",
            "role",
            name=op.f("uq_change_revisions_change_id_component_revision_id_role"),
        ),
    )
    op.create_index(op.f("ix_change_revisions_change_id"), "change_revisions", ["change_id"])
    op.create_index(
        op.f("ix_change_revisions_component_revision_id"),
        "change_revisions",
        ["component_revision_id"],
    )
    _link_table("change_experiments", "experiment_id", "experiments")
    _link_table("change_test_runs", "test_run_id", "test_runs")


def downgrade() -> None:
    op.drop_table("change_test_runs")
    op.drop_table("change_experiments")
    op.drop_table("change_revisions")
    op.drop_table("engineering_changes")
    for table in ("part_instances", "component_revisions"):
        op.drop_constraint(op.f(f"fk_{table}_supplier_id_suppliers"), table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_supplier_id"), table_name=table)
        op.drop_column(table, "supplier_id")
    op.drop_table("suppliers")
