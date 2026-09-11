"""Small helpers that build domain objects through the service layer (never raw rows)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.lifecycle import LifecycleState
from nemeth.modules.bom import service as bom
from nemeth.modules.bom.models import BomLine
from nemeth.modules.bom.schemas import BomLineCreate
from nemeth.modules.components import service as components
from nemeth.modules.components.models import (
    Component,
    ComponentFamily,
    ComponentKind,
    ComponentRevision,
)
from nemeth.modules.components.schemas import ComponentCreate, RevisionContent


def make_component(
    session: Session,
    actor: Actor,
    identifier: str,
    name: str | None = None,
    *,
    kind: ComponentKind = ComponentKind.PART,
    family: ComponentFamily = ComponentFamily.MVT,
    material: str | None = None,
) -> Component:
    return components.create_component(
        session,
        actor,
        ComponentCreate(
            identifier=identifier,
            name=name or identifier,
            kind=kind,
            family=family,
            initial_revision=RevisionContent(material=material),
        ),
    )


def make_assembly(
    session: Session, actor: Actor, identifier: str, name: str | None = None
) -> Component:
    return make_component(session, actor, identifier, name, kind=ComponentKind.ASSEMBLY)


def latest(session: Session, component: Component) -> ComponentRevision:
    assert component.latest_revision is not None
    return components.get_revision(session, component.latest_revision.id)


def add_line(
    session: Session,
    actor: Actor,
    parent: Component,
    child: Component,
    quantity: int = 1,
    *,
    pin: ComponentRevision | None = None,
) -> BomLine:
    return bom.add_line(
        session,
        actor,
        latest(session, parent),
        BomLineCreate(
            child_component_id=child.id,
            quantity=Decimal(quantity),
            child_revision_id=pin.id if pin else None,
        ),
    )


def freeze(session: Session, actor: Actor, revision: ComponentRevision) -> ComponentRevision:
    """CONCEPT → DESIGN → PROTOTYPE."""
    components.transition_revision(session, actor, revision, LifecycleState.DESIGN)
    return components.transition_revision(session, actor, revision, LifecycleState.PROTOTYPE)


def release(session: Session, actor: Actor, revision: ComponentRevision) -> ComponentRevision:
    freeze(session, actor, revision)
    components.transition_revision(session, actor, revision, LifecycleState.VALIDATION)
    return components.transition_revision(session, actor, revision, LifecycleState.RELEASED)
