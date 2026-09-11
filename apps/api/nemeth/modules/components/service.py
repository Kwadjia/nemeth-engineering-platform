"""Domain rules for components and revisions. The only place that writes these tables."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from nemeth.core.audit import stamp_created, stamp_updated
from nemeth.core.auth import Actor
from nemeth.core.errors import (
    DomainValidationError,
    DuplicateIdentifierError,
    ImmutableRevisionError,
    NotFoundError,
)
from nemeth.core.identifiers import next_identifier, normalize_identifier, revision_label
from nemeth.core.lifecycle import LifecycleState, assert_transition, is_frozen
from nemeth.core.lookup import get_by_ref
from nemeth.core.pagination import PageParams
from nemeth.modules.bom.models import BomLine
from nemeth.modules.components.models import (
    Component,
    ComponentFamily,
    ComponentKind,
    ComponentRevision,
)
from nemeth.modules.components.schemas import (
    ComponentCreate,
    ComponentUpdate,
    RevisionContent,
    RevisionCreate,
    RevisionUpdate,
)

_WITH_REVISIONS = (selectinload(Component.revisions),)


# --- queries -----------------------------------------------------------------------


def identifier_exists(session: Session, identifier: str) -> bool:
    stmt = select(func.count()).select_from(Component).where(Component.identifier == identifier)
    return bool(session.execute(stmt).scalar_one())


def get_component(session: Session, ref: str) -> Component:
    return get_by_ref(session, Component, ref, options=_WITH_REVISIONS, label="Component")


def get_component_by_id(session: Session, component_id: uuid.UUID) -> Component:
    return get_component(session, str(component_id))


def list_components(
    session: Session,
    *,
    page: PageParams,
    q: str | None = None,
    family: ComponentFamily | None = None,
    kind: ComponentKind | None = None,
    state: LifecycleState | None = None,
    placeholder: bool | None = None,
) -> tuple[list[Component], int]:
    stmt = select(Component)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(Component.identifier.ilike(pattern), Component.name.ilike(pattern)))
    if family is not None:
        stmt = stmt.where(Component.family == family)
    if kind is not None:
        stmt = stmt.where(Component.kind == kind)
    if placeholder is not None:
        stmt = stmt.where(Component.is_placeholder == placeholder)
    if state is not None:
        latest = (
            select(
                ComponentRevision.component_id,
                func.max(ComponentRevision.revision_number).label("n"),
            )
            .group_by(ComponentRevision.component_id)
            .subquery()
        )
        stmt = (
            stmt.join(latest, latest.c.component_id == Component.id)
            .join(
                ComponentRevision,
                (ComponentRevision.component_id == Component.id)
                & (ComponentRevision.revision_number == latest.c.n),
            )
            .where(ComponentRevision.lifecycle_state == state)
        )
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = (
        stmt.options(*_WITH_REVISIONS)
        .order_by(Component.identifier)
        .limit(page.limit)
        .offset(page.offset)
    )
    items = list(session.execute(stmt).scalars().unique())
    return items, int(total)


def count_by_state(session: Session) -> dict[str, int]:
    """Number of components grouped by the lifecycle state of their latest revision."""
    latest = (
        select(
            ComponentRevision.component_id,
            func.max(ComponentRevision.revision_number).label("n"),
        )
        .group_by(ComponentRevision.component_id)
        .subquery()
    )
    stmt = (
        select(ComponentRevision.lifecycle_state, func.count())
        .join(
            latest,
            (ComponentRevision.component_id == latest.c.component_id)
            & (ComponentRevision.revision_number == latest.c.n),
        )
        .group_by(ComponentRevision.lifecycle_state)
    )
    counts = {state.value: 0 for state in LifecycleState}
    for state, count in session.execute(stmt).all():
        counts[LifecycleState(state).value] = int(count)
    return counts


def get_revision(session: Session, revision_id: uuid.UUID) -> ComponentRevision:
    stmt = (
        select(ComponentRevision)
        .where(ComponentRevision.id == revision_id)
        .options(
            selectinload(ComponentRevision.component).selectinload(Component.revisions),
            selectinload(ComponentRevision.bom_lines),
        )
    )
    revision = session.execute(stmt).scalar_one_or_none()
    if revision is None:
        raise NotFoundError(f"Revision {revision_id} not found", resource="ComponentRevision")
    return revision


def get_revision_by_label(session: Session, component: Component, label: str) -> ComponentRevision:
    wanted = label.strip().upper().removeprefix("REV").strip()
    for revision in component.revisions:
        if revision.revision_label == wanted:
            return revision
    raise NotFoundError(
        f"{component.identifier} has no revision {label!r}",
        resource="ComponentRevision",
        component=component.identifier,
        label=label,
    )


def recent_revisions(session: Session, limit: int = 10) -> list[ComponentRevision]:
    stmt = (
        select(ComponentRevision)
        .options(selectinload(ComponentRevision.component))
        .order_by(ComponentRevision.created_at.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars())


# --- guards ------------------------------------------------------------------------


def assert_editable(revision: ComponentRevision) -> None:
    if revision.is_frozen:
        raise ImmutableRevisionError(
            f"{revision.display_identifier} is {revision.lifecycle_state.value} and cannot be "
            "modified. Create a new revision instead.",
            revision_id=str(revision.id),
            lifecycle_state=revision.lifecycle_state.value,
        )


# --- commands ----------------------------------------------------------------------


def _apply_content(
    revision: ComponentRevision, content: RevisionContent, *, only_set: bool
) -> None:
    data = content.model_dump(exclude_unset=only_set)
    for field, value in data.items():
        setattr(revision, field, value)


def create_component(session: Session, actor: Actor, data: ComponentCreate) -> Component:
    if data.identifier is not None:
        identifier = normalize_identifier(data.identifier)
        if identifier_exists(session, identifier):
            raise DuplicateIdentifierError(
                f"Component {identifier} already exists", identifier=identifier
            )
    else:
        assert data.product_code is not None  # guaranteed by schema validator
        prefix = f"{normalize_identifier(data.product_code)}-{data.family.value}"
        identifier = next_identifier(
            session, prefix, exists=lambda candidate: identifier_exists(session, candidate)
        )

    component = Component(
        identifier=identifier,
        name=data.name.strip(),
        kind=data.kind,
        family=data.family,
        description=data.description,
        is_placeholder=data.is_placeholder,
    )
    stamp_created(component, actor)

    initial = ComponentRevision(
        revision_number=1,
        revision_label=revision_label(1),
        lifecycle_state=LifecycleState.CONCEPT,
        change_summary=data.change_summary,
    )
    if data.initial_revision is not None:
        _apply_content(initial, data.initial_revision, only_set=False)
    stamp_created(initial, actor)
    component.revisions.append(initial)

    session.add(component)
    session.flush()
    return component


def update_component(
    session: Session, actor: Actor, component: Component, data: ComponentUpdate
) -> Component:
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        component.name = changes["name"].strip()
    if "description" in changes:
        component.description = changes["description"]
    if "is_placeholder" in changes and changes["is_placeholder"] is not None:
        component.is_placeholder = changes["is_placeholder"]
    stamp_updated(component, actor)
    session.flush()
    return component


def create_revision(
    session: Session, actor: Actor, component: Component, data: RevisionCreate
) -> ComponentRevision:
    # Serialise revision creation per component so numbering is race-free.
    session.execute(select(Component.id).where(Component.id == component.id).with_for_update())
    session.refresh(component, attribute_names=["revisions"])

    if data.from_revision_id is not None:
        source = next((r for r in component.revisions if r.id == data.from_revision_id), None)
        if source is None:
            raise DomainValidationError(
                "from_revision_id must reference a revision of the same component",
                field="from_revision_id",
            )
    else:
        source = component.latest_revision
    if source is None:  # pragma: no cover - every component is created with revision A
        raise DomainValidationError("component has no revisions to copy from")

    number = (component.latest_revision.revision_number if component.latest_revision else 0) + 1
    revision = ComponentRevision(
        component_id=component.id,
        revision_number=number,
        revision_label=revision_label(number),
        lifecycle_state=LifecycleState.CONCEPT,
        change_summary=data.change_summary,
    )
    for field in ComponentRevision.CONTENT_FIELDS:
        setattr(revision, field, getattr(source, field))
    if data.content is not None:
        _apply_content(revision, data.content, only_set=True)
    stamp_created(revision, actor)
    session.add(revision)
    session.flush()

    if data.copy_bom:
        for line in source.bom_lines:
            copy = BomLine(
                child_component_id=line.child_component_id,
                child_revision_id=line.child_revision_id,
                find_number=line.find_number,
                quantity=line.quantity,
                unit=line.unit,
                reference_designator=line.reference_designator,
                notes=line.notes,
            )
            stamp_created(copy, actor)
            revision.bom_lines.append(copy)

    if source.superseded_by_id is None:
        source.superseded_by_id = revision.id
        stamp_updated(source, actor)

    component.revisions.append(revision)
    stamp_updated(component, actor)
    session.flush()
    return revision


def update_revision(
    session: Session, actor: Actor, revision: ComponentRevision, data: RevisionUpdate
) -> ComponentRevision:
    assert_editable(revision)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(revision, field, value)
    stamp_updated(revision, actor)
    session.flush()
    return revision


def transition_revision(
    session: Session, actor: Actor, revision: ComponentRevision, target: LifecycleState
) -> ComponentRevision:
    assert_transition(revision.lifecycle_state, target)
    revision.lifecycle_state = target
    if is_frozen(target) and revision.frozen_at is None:
        revision.frozen_at = datetime.now(tz=UTC)
    stamp_updated(revision, actor)
    session.flush()
    return revision
