"""Core PLM: identifier counters, products, calibers, product models, components,
component revisions and BOM lines.

Revision ID: 0001
Revises:
Create Date: 2026-09-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

LIFECYCLE_STATES = ("CONCEPT", "DESIGN", "PROTOTYPE", "VALIDATION", "RELEASED", "OBSOLETE")
COMPONENT_KINDS = ("PART", "ASSEMBLY")
COMPONENT_FAMILIES = ("WATCH", "CASE", "DIAL", "HAND", "MVT", "STRAP", "PKG", "MISC")


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
        "identifier_counters",
        sa.Column("prefix", sa.String(64), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("prefix", name=op.f("pk_identifier_counters")),
    )

    op.create_table(
        "components",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", _enum(COMPONENT_KINDS, "component_kind"), nullable=False),
        sa.Column("family", _enum(COMPONENT_FAMILIES, "component_family"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_components")),
    )
    op.create_index(op.f("ix_components_identifier"), "components", ["identifier"], unique=True)
    op.create_index(op.f("ix_components_family"), "components", ["family"], unique=False)

    op.create_table(
        "component_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("component_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("revision_label", sa.String(8), nullable=False),
        sa.Column("lifecycle_state", _enum(LIFECYCLE_STATES, "lifecycle_state"), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("material", sa.String(200), nullable=True),
        sa.Column("heat_treatment", sa.String(200), nullable=True),
        sa.Column("finish", sa.String(200), nullable=True),
        sa.Column("manufacturing_method", sa.String(200), nullable=True),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tolerances", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("mass_g", sa.Numeric(10, 4), nullable=True),
        sa.Column("supplier_note", sa.String(300), nullable=True),
        sa.Column("inspection_requirements", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by_id", sa.Uuid(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["components.id"],
            name=op.f("fk_component_revisions_component_id_components"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_component_revisions")),
        sa.UniqueConstraint(
            "component_id",
            "revision_number",
            name=op.f("uq_component_revisions_component_id_revision_number"),
        ),
        sa.UniqueConstraint(
            "component_id",
            "revision_label",
            name=op.f("uq_component_revisions_component_id_revision_label"),
        ),
    )
    op.create_index(
        op.f("ix_component_revisions_component_id"), "component_revisions", ["component_id"]
    )
    op.create_index(
        op.f("ix_component_revisions_lifecycle_state"), "component_revisions", ["lifecycle_state"]
    )
    op.create_foreign_key(
        op.f("fk_component_revisions_superseded_by_id_component_revisions"),
        "component_revisions",
        "component_revisions",
        ["superseded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "bom_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_revision_id", sa.Uuid(), nullable=False),
        sa.Column("child_component_id", sa.Uuid(), nullable=False),
        sa.Column("child_revision_id", sa.Uuid(), nullable=True),
        sa.Column("find_number", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(16), nullable=False),
        sa.Column("reference_designator", sa.String(120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_bom_lines_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["parent_revision_id"],
            ["component_revisions.id"],
            name=op.f("fk_bom_lines_parent_revision_id_component_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["child_component_id"],
            ["components.id"],
            name=op.f("fk_bom_lines_child_component_id_components"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["child_revision_id"],
            ["component_revisions.id"],
            name=op.f("fk_bom_lines_child_revision_id_component_revisions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bom_lines")),
        sa.UniqueConstraint(
            "parent_revision_id",
            "find_number",
            name=op.f("uq_bom_lines_parent_revision_id_find_number"),
        ),
    )
    op.create_index(op.f("ix_bom_lines_parent_revision_id"), "bom_lines", ["parent_revision_id"])
    op.create_index(op.f("ix_bom_lines_child_component_id"), "bom_lines", ["child_component_id"])
    op.create_index(op.f("ix_bom_lines_child_revision_id"), "bom_lines", ["child_revision_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lifecycle_state", _enum(LIFECYCLE_STATES, "lifecycle_state"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(op.f("ix_products_identifier"), "products", ["identifier"], unique=True)

    op.create_table(
        "calibers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lifecycle_state", _enum(LIFECYCLE_STATES, "lifecycle_state"), nullable=False),
        sa.Column("root_component_id", sa.Uuid(), nullable=True),
        sa.Column("architecture", sa.String(300), nullable=True),
        sa.Column("diameter_mm", sa.Numeric(7, 3), nullable=True),
        sa.Column("thickness_mm", sa.Numeric(7, 3), nullable=True),
        sa.Column("frequency_bph", sa.Integer(), nullable=True),
        sa.Column("jewel_count", sa.Integer(), nullable=True),
        sa.Column("power_reserve_hours", sa.Numeric(6, 1), nullable=True),
        sa.Column("lift_angle_deg", sa.Numeric(5, 2), nullable=True),
        sa.Column("target_amplitude_deg", sa.Integer(), nullable=True),
        sa.Column("target_rate_tolerance_spd", sa.Numeric(5, 2), nullable=True),
        sa.Column("specification", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["root_component_id"],
            ["components.id"],
            name=op.f("fk_calibers_root_component_id_components"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calibers")),
    )
    op.create_index(op.f("ix_calibers_identifier"), "calibers", ["identifier"], unique=True)

    op.create_table(
        "product_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lifecycle_state", _enum(LIFECYCLE_STATES, "lifecycle_state"), nullable=False),
        sa.Column("caliber_id", sa.Uuid(), nullable=True),
        sa.Column("root_component_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_models_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["caliber_id"],
            ["calibers.id"],
            name=op.f("fk_product_models_caliber_id_calibers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["root_component_id"],
            ["components.id"],
            name=op.f("fk_product_models_root_component_id_components"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_models")),
    )
    op.create_index(
        op.f("ix_product_models_identifier"), "product_models", ["identifier"], unique=True
    )
    op.create_index(op.f("ix_product_models_product_id"), "product_models", ["product_id"])


def downgrade() -> None:
    op.drop_table("product_models")
    op.drop_table("calibers")
    op.drop_table("products")
    op.drop_table("bom_lines")
    op.drop_constraint(
        op.f("fk_component_revisions_superseded_by_id_component_revisions"),
        "component_revisions",
        type_="foreignkey",
    )
    op.drop_table("component_revisions")
    op.drop_table("components")
    op.drop_table("identifier_counters")
