"""NEMETH N1 placeholder seed.

Creates the N1 product, the N1.01 reference, Caliber N1, prototype N1-P001 and a sample
component tree with a nested BOM. Every record is flagged ``is_placeholder`` and its
notes say so; replace values as real engineering data arrives.

The seed is idempotent per record: each entity is created only if its identifier is
missing, so a database seeded by an earlier slice gains the new records on re-run.

Experiments EXP-001…EXP-003 (ST36 disassembly, reassembly and baseline timing) are
seeded by the experiment slice once those tables exist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.identifiers import ensure_counter_at_least
from nemeth.core.lifecycle import LifecycleState
from nemeth.modules.bom import service as bom
from nemeth.modules.bom.schemas import BomLineCreate
from nemeth.modules.components import service as components
from nemeth.modules.components.models import Component, ComponentFamily, ComponentKind
from nemeth.modules.components.schemas import ComponentCreate, RevisionContent
from nemeth.modules.products import service as products
from nemeth.modules.products.models import Caliber, Product, ProductModel
from nemeth.modules.products.schemas import CaliberCreate, ProductCreate, ProductModelCreate
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.models import Prototype, PrototypeStatus
from nemeth.modules.prototypes.schemas import PrototypeCreate

SEED_ACTOR = Actor(id="seed", display_name="Seed script")
PLACEHOLDER = "PLACEHOLDER — sample data from the N1 seed. Replace with real engineering data."


@dataclass
class SeedResult:
    components: int = 0
    bom_lines: int = 0
    records: list[str] = field(default_factory=list)

    @property
    def created(self) -> bool:
        return bool(self.components or self.bom_lines or self.records)

    def summary(self) -> str:
        if not self.created:
            return "N1 seed already present; nothing to do."
        parts = []
        if self.records:
            parts.append(", ".join(self.records))
        if self.components:
            parts.append(f"{self.components} components")
        if self.bom_lines:
            parts.append(f"{self.bom_lines} BOM lines")
        return "Seeded NEMETH N1: " + "; ".join(parts) + "."


@dataclass(frozen=True)
class Spec:
    identifier: str
    name: str
    family: ComponentFamily
    kind: ComponentKind = ComponentKind.PART
    material: str | None = None
    finish: str | None = None
    manufacturing_method: str | None = None
    description: str | None = None


# Identifiers follow docs/architecture/identifiers.md: {PRODUCT}-{FAMILY}-{NNN}.
COMPONENTS: tuple[Spec, ...] = (
    Spec(
        "N1-WATCH-001",
        "N1 Watch Assembly",
        ComponentFamily.WATCH,
        ComponentKind.ASSEMBLY,
        description="Top-level assembly for reference N1.01.",
    ),
    # --- case --------------------------------------------------------------------
    Spec("N1-CASE-001", "Case Assembly", ComponentFamily.CASE, ComponentKind.ASSEMBLY),
    Spec(
        "N1-CASE-002",
        "Case Middle",
        ComponentFamily.CASE,
        material="316L stainless steel",
        finish="Brushed flanks, polished bevels",
        manufacturing_method="CNC milling + hand finishing",
    ),
    Spec(
        "N1-CASE-003",
        "Bezel",
        ComponentFamily.CASE,
        material="316L stainless steel",
        finish="Polished",
        manufacturing_method="CNC turning",
    ),
    Spec(
        "N1-CASE-004",
        "Sapphire Crystal",
        ComponentFamily.CASE,
        material="Sapphire, AR coated inside",
        manufacturing_method="External supplier",
    ),
    Spec(
        "N1-CASE-005",
        "Crown",
        ComponentFamily.CASE,
        material="316L stainless steel",
        finish="Brushed",
        manufacturing_method="CNC turning",
    ),
    Spec(
        "N1-CASE-006",
        "Caseback",
        ComponentFamily.CASE,
        material="316L stainless steel",
        finish="Brushed, sapphire display window",
        manufacturing_method="CNC turning",
    ),
    # --- dial and hands -----------------------------------------------------------
    Spec("N1-DIAL-001", "Dial Assembly", ComponentFamily.DIAL, ComponentKind.ASSEMBLY),
    Spec(
        "N1-DIAL-002",
        "Dial",
        ComponentFamily.DIAL,
        material="Brass CuZn37",
        finish="Dark navy galvanic, brushed",
        manufacturing_method="Stamping + galvanic finishing",
    ),
    Spec(
        "N1-DIAL-003",
        "Hour Markers",
        ComponentFamily.DIAL,
        material="316L stainless steel",
        finish="Polished",
        manufacturing_method="Wire EDM + polishing",
    ),
    Spec(
        "N1-HAND-001",
        "Hour Hand",
        ComponentFamily.HAND,
        material="Steel",
        finish="Heat-blued",
        manufacturing_method="Stamping + heat treatment",
    ),
    Spec(
        "N1-HAND-002",
        "Minute Hand",
        ComponentFamily.HAND,
        material="Steel",
        finish="Heat-blued",
        manufacturing_method="Stamping + heat treatment",
    ),
    Spec(
        "N1-HAND-003",
        "Seconds Hand",
        ComponentFamily.HAND,
        material="Steel",
        finish="Heat-blued",
        manufacturing_method="Stamping + heat treatment",
    ),
    # --- movement (Caliber N1) ----------------------------------------------------
    Spec(
        "N1-MVT-001",
        "Caliber N1 Movement Assembly",
        ComponentFamily.MVT,
        ComponentKind.ASSEMBLY,
        description="Root assembly of Caliber N1.",
    ),
    Spec(
        "N1-MVT-002",
        "Mainplate",
        ComponentFamily.MVT,
        material="Brass CuZn39Pb3",
        finish="Rhodium plated, perlage",
        manufacturing_method="CNC milling",
    ),
    Spec("N1-MVT-003", "Barrel Assembly", ComponentFamily.MVT, ComponentKind.ASSEMBLY),
    Spec(
        "N1-MVT-004",
        "Barrel",
        ComponentFamily.MVT,
        material="Brass CuZn39Pb3",
        manufacturing_method="CNC turning + gear cutting",
    ),
    Spec(
        "N1-MVT-005",
        "Mainspring",
        ComponentFamily.MVT,
        material="Nivaflex alloy",
        manufacturing_method="External supplier",
    ),
    Spec(
        "N1-MVT-006",
        "Barrel Arbor",
        ComponentFamily.MVT,
        material="Steel 20AP",
        finish="Polished pivots",
        manufacturing_method="CNC turning + heat treatment",
    ),
    Spec("N1-MVT-007", "Gear Train", ComponentFamily.MVT, ComponentKind.ASSEMBLY),
    Spec(
        "N1-MVT-008",
        "Center Wheel",
        ComponentFamily.MVT,
        material="Brass CuZn39Pb3",
        manufacturing_method="Gear cutting",
    ),
    Spec(
        "N1-MVT-009",
        "Third Wheel",
        ComponentFamily.MVT,
        material="Brass CuZn39Pb3",
        manufacturing_method="Gear cutting",
    ),
    Spec(
        "N1-MVT-010",
        "Fourth Wheel",
        ComponentFamily.MVT,
        material="Brass CuZn39Pb3",
        manufacturing_method="Gear cutting",
    ),
    Spec(
        "N1-MVT-011",
        "Escape Wheel",
        ComponentFamily.MVT,
        material="Steel",
        finish="Polished teeth",
        manufacturing_method="Wire EDM + polishing",
    ),
    Spec("N1-MVT-012", "Escapement", ComponentFamily.MVT, ComponentKind.ASSEMBLY),
    Spec(
        "N1-MVT-013",
        "Pallet Fork",
        ComponentFamily.MVT,
        material="Steel",
        finish="Polished",
        manufacturing_method="Wire EDM + polishing",
    ),
    Spec(
        "N1-MVT-014",
        "Balance Assembly",
        ComponentFamily.MVT,
        ComponentKind.ASSEMBLY,
        description="Balance wheel, hairspring, staff and roller. Sub-components to be defined.",
    ),
    Spec(
        "N1-MVT-015",
        "Bridges",
        ComponentFamily.MVT,
        ComponentKind.ASSEMBLY,
        description="Barrel bridge, train bridge, balance cock. Sub-components to be defined.",
    ),
    Spec(
        "N1-MVT-016",
        "Keyless Works",
        ComponentFamily.MVT,
        ComponentKind.ASSEMBLY,
        description="Winding and setting mechanism. Sub-components to be defined.",
    ),
)

# (parent, child, quantity)
BOM: tuple[tuple[str, str, int], ...] = (
    ("N1-WATCH-001", "N1-CASE-001", 1),
    ("N1-WATCH-001", "N1-DIAL-001", 1),
    ("N1-WATCH-001", "N1-MVT-001", 1),
    ("N1-CASE-001", "N1-CASE-002", 1),
    ("N1-CASE-001", "N1-CASE-003", 1),
    ("N1-CASE-001", "N1-CASE-004", 1),
    ("N1-CASE-001", "N1-CASE-005", 1),
    ("N1-CASE-001", "N1-CASE-006", 1),
    ("N1-DIAL-001", "N1-DIAL-002", 1),
    ("N1-DIAL-001", "N1-DIAL-003", 12),
    ("N1-DIAL-001", "N1-HAND-001", 1),
    ("N1-DIAL-001", "N1-HAND-002", 1),
    ("N1-DIAL-001", "N1-HAND-003", 1),
    ("N1-MVT-001", "N1-MVT-002", 1),
    ("N1-MVT-001", "N1-MVT-003", 1),
    ("N1-MVT-001", "N1-MVT-007", 1),
    ("N1-MVT-001", "N1-MVT-012", 1),
    ("N1-MVT-001", "N1-MVT-014", 1),
    ("N1-MVT-001", "N1-MVT-015", 1),
    ("N1-MVT-001", "N1-MVT-016", 1),
    ("N1-MVT-003", "N1-MVT-004", 1),
    ("N1-MVT-003", "N1-MVT-005", 1),
    ("N1-MVT-003", "N1-MVT-006", 1),
    ("N1-MVT-007", "N1-MVT-008", 1),
    ("N1-MVT-007", "N1-MVT-009", 1),
    ("N1-MVT-007", "N1-MVT-010", 1),
    ("N1-MVT-007", "N1-MVT-011", 1),
    ("N1-MVT-012", "N1-MVT-013", 1),
)

SeedModel = type[Product] | type[ProductModel] | type[Caliber] | type[Component] | type[Prototype]


def _exists(session: Session, model: SeedModel, identifier: str) -> bool:
    return (
        session.execute(select(model.id).where(model.identifier == identifier)).first() is not None
    )


def _sync_counters(session: Session) -> None:
    """Advance identifier counters past the hand-assigned seed identifiers."""
    highest: dict[str, int] = {}
    for spec in COMPONENTS:
        match = re.match(r"^(.*)-(\d+)$", spec.identifier)
        if match:
            prefix, number = match.group(1), int(match.group(2))
            highest[prefix] = max(highest.get(prefix, 0), number)
    for prefix, value in highest.items():
        ensure_counter_at_least(session, prefix, value)
    ensure_counter_at_least(session, "N1-P", 1)


def _seed_components(session: Session, result: SeedResult) -> dict[str, Component]:
    created: dict[str, Component] = {}
    for spec in COMPONENTS:
        if _exists(session, Component, spec.identifier):
            created[spec.identifier] = components.get_component(session, spec.identifier)
            continue
        created[spec.identifier] = components.create_component(
            session,
            SEED_ACTOR,
            ComponentCreate(
                identifier=spec.identifier,
                name=spec.name,
                kind=spec.kind,
                family=spec.family,
                description=spec.description,
                is_placeholder=True,
                change_summary="Initial revision (seed)",
                initial_revision=RevisionContent(
                    material=spec.material,
                    finish=spec.finish,
                    manufacturing_method=spec.manufacturing_method,
                    notes=PLACEHOLDER,
                ),
            ),
        )
        result.components += 1
    return created


def _seed_bom(session: Session, created: dict[str, Component], result: SeedResult) -> None:
    for parent_id, child_id, quantity in BOM:
        parent = created[parent_id]
        assert parent.latest_revision is not None
        revision = components.get_revision(session, parent.latest_revision.id)
        if any(line.child_component_id == created[child_id].id for line in revision.bom_lines):
            continue
        if revision.is_frozen:
            continue  # the seed assembly has been advanced by hand; leave its history alone
        bom.add_line(
            session,
            SEED_ACTOR,
            revision,
            BomLineCreate(child_component_id=created[child_id].id, quantity=Decimal(quantity)),
        )
        result.bom_lines += 1


def seed_n1(session: Session) -> SeedResult:
    result = SeedResult()
    created = _seed_components(session, result)
    _seed_bom(session, created, result)
    _sync_counters(session)

    if _exists(session, Product, "N1"):
        product = products.get_product(session, "N1")
    else:
        product = products.create_product(
            session,
            SEED_ACTOR,
            ProductCreate(
                identifier="N1",
                name="NEMETH N1",
                description="The flagship mechanical watch from NEMETH Detroit.",
                lifecycle_state=LifecycleState.CONCEPT,
                notes=PLACEHOLDER,
                is_placeholder=True,
            ),
        )
        result.records.append("product N1")

    if _exists(session, Caliber, "CAL-N1"):
        caliber = products.get_caliber(session, "CAL-N1")
    else:
        caliber = products.create_caliber(
            session,
            SEED_ACTOR,
            CaliberCreate(
                identifier="CAL-N1",
                name="Caliber N1",
                description="First in-house manual-wind caliber for the N1.",
                lifecycle_state=LifecycleState.CONCEPT,
                root_component_id=created["N1-MVT-001"].id,
                architecture="Manual wind, single barrel, Swiss lever escapement (to be confirmed)",
                specification={
                    "_placeholder": True,
                    "note": "Specification to be defined during the concept phase.",
                },
                notes=PLACEHOLDER,
                is_placeholder=True,
            ),
        )
        result.records.append("caliber CAL-N1")

    if _exists(session, ProductModel, "N1.01"):
        model = products.get_model(session, "N1.01")
    else:
        model = products.create_model(
            session,
            SEED_ACTOR,
            product,
            ProductModelCreate(
                identifier="N1.01",
                name="N1 Reference 01",
                description="First reference of the NEMETH N1.",
                lifecycle_state=LifecycleState.CONCEPT,
                caliber_id=caliber.id,
                root_component_id=created["N1-WATCH-001"].id,
                notes=PLACEHOLDER,
                is_placeholder=True,
            ),
        )
        result.records.append("model N1.01")

    if not _exists(session, Prototype, "N1-P001"):
        prototypes.create_prototype(
            session,
            SEED_ACTOR,
            PrototypeCreate(
                identifier="N1-P001",
                name="N1 first prototype",
                purpose=(
                    "First physical N1 build: validate case, dial and hand fit around the "
                    "Caliber N1 concept and establish the assembly procedure."
                ),
                status=PrototypeStatus.PLANNED,
                product_model_id=model.id,
                caliber_id=caliber.id,
                notes=PLACEHOLDER,
                is_placeholder=True,
            ),
        )
        result.records.append("prototype N1-P001")

    session.flush()
    return result
