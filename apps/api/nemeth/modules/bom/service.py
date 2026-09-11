"""BOM rules: line management on assembly revisions, cycle prevention, resolution,
flattening and where-used (ADR-006)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from nemeth.core.audit import stamp_created, stamp_updated
from nemeth.core.auth import Actor
from nemeth.core.errors import BomCycleError, DomainValidationError, NotFoundError
from nemeth.core.lifecycle import LifecycleState
from nemeth.modules.bom.models import BomLine
from nemeth.modules.bom.schemas import (
    BomFlat,
    BomFlatRow,
    BomLineCreate,
    BomLineRead,
    BomLineUpdate,
    BomNode,
    BomTree,
    ResolutionSource,
    ResolveMode,
    WhereUsedRow,
)
from nemeth.modules.components import service as components
from nemeth.modules.components.models import Component, ComponentKind, ComponentRevision
from nemeth.modules.components.schemas import ComponentSummary, RevisionSummary

MAX_DEPTH = 32


# --- queries -----------------------------------------------------------------------


def get_line(session: Session, line_id: uuid.UUID) -> BomLine:
    stmt = (
        select(BomLine)
        .where(BomLine.id == line_id)
        .options(
            selectinload(BomLine.parent_revision).selectinload(ComponentRevision.component),
            selectinload(BomLine.child_component).selectinload(Component.revisions),
            selectinload(BomLine.child_revision),
        )
    )
    line = session.execute(stmt).scalar_one_or_none()
    if line is None:
        raise NotFoundError(f"BOM line {line_id} not found", resource="BomLine")
    return line


def reachable_components(session: Session, start: uuid.UUID) -> set[uuid.UUID]:
    """Every component reachable downward from ``start`` through any revision's BOM lines."""
    seen: set[uuid.UUID] = set()
    frontier: set[uuid.UUID] = {start}
    while frontier:
        stmt = (
            select(BomLine.child_component_id)
            .join(ComponentRevision, BomLine.parent_revision_id == ComponentRevision.id)
            .where(ComponentRevision.component_id.in_(frontier))
        )
        found = {row[0] for row in session.execute(stmt).all()}
        frontier = found - seen
        seen |= found
    return seen


def where_used(session: Session, component: Component) -> list[WhereUsedRow]:
    """Assembly revisions whose BOM references ``component`` (any revision, pinned or not)."""
    stmt = (
        select(BomLine)
        .where(BomLine.child_component_id == component.id)
        .options(
            selectinload(BomLine.parent_revision).selectinload(ComponentRevision.component),
            selectinload(BomLine.child_component),
            selectinload(BomLine.child_revision),
        )
        .join(ComponentRevision, BomLine.parent_revision_id == ComponentRevision.id)
        .join(Component, ComponentRevision.component_id == Component.id)
        .order_by(Component.identifier, ComponentRevision.revision_number.desc())
    )
    rows = []
    for line in session.execute(stmt).scalars():
        rows.append(
            WhereUsedRow(
                parent_component=ComponentSummary.model_validate(line.parent_revision.component),
                parent_revision=RevisionSummary.model_validate(line.parent_revision),
                line=BomLineRead.model_validate(line),
            )
        )
    return rows


def assembly_count(session: Session) -> int:
    stmt = (
        select(func.count()).select_from(Component).where(Component.kind == ComponentKind.ASSEMBLY)
    )
    return int(session.execute(stmt).scalar_one())


# --- commands ----------------------------------------------------------------------


def _assert_assembly(revision: ComponentRevision) -> None:
    if revision.component.kind != ComponentKind.ASSEMBLY:
        raise DomainValidationError(
            f"{revision.component.identifier} is a {revision.component.kind.value}; only "
            "assemblies have BOM lines.",
            component=revision.component.identifier,
        )


def _resolve_child(session: Session, data: BomLineCreate) -> Component:
    if data.child_component_id is not None:
        return components.get_component_by_id(session, data.child_component_id)
    assert data.child_component_identifier is not None
    return components.get_component(session, data.child_component_identifier)


def _assert_pin_belongs(session: Session, child: Component, pin_id: uuid.UUID | None) -> None:
    if pin_id is None:
        return
    if not any(r.id == pin_id for r in child.revisions):
        raise DomainValidationError(
            f"child_revision_id does not belong to {child.identifier}",
            field="child_revision_id",
        )


def add_line(
    session: Session, actor: Actor, parent: ComponentRevision, data: BomLineCreate
) -> BomLine:
    _assert_assembly(parent)
    components.assert_editable(parent)
    child = _resolve_child(session, data)

    if child.id == parent.component_id:
        raise BomCycleError(f"{child.identifier} cannot contain itself")
    if parent.component_id in reachable_components(session, child.id):
        raise BomCycleError(
            f"Adding {child.identifier} to {parent.display_identifier} would create a cycle: "
            f"{child.identifier} already contains {parent.component.identifier}.",
            parent=parent.component.identifier,
            child=child.identifier,
        )
    _assert_pin_belongs(session, child, data.child_revision_id)

    find_number = data.find_number
    if find_number is None:
        current_max = max((line.find_number for line in parent.bom_lines), default=0)
        find_number = current_max + 10
    elif any(line.find_number == find_number for line in parent.bom_lines):
        raise DomainValidationError(
            f"find number {find_number} already used on {parent.display_identifier}",
            field="find_number",
        )

    line = BomLine(
        parent_revision_id=parent.id,
        child_component_id=child.id,
        child_revision_id=data.child_revision_id,
        find_number=find_number,
        quantity=data.quantity,
        unit=data.unit,
        reference_designator=data.reference_designator,
        notes=data.notes,
    )
    stamp_created(line, actor)
    parent.bom_lines.append(line)
    stamp_updated(parent, actor)
    session.flush()
    return get_line(session, line.id)


def update_line(session: Session, actor: Actor, line: BomLine, data: BomLineUpdate) -> BomLine:
    components.assert_editable(line.parent_revision)
    changes = data.model_dump(exclude_unset=True)
    if "child_revision_id" in changes:
        _assert_pin_belongs(session, line.child_component, changes["child_revision_id"])
    if "find_number" in changes and changes["find_number"] != line.find_number:
        siblings = line.parent_revision.bom_lines
        if any(s.id != line.id and s.find_number == changes["find_number"] for s in siblings):
            raise DomainValidationError(
                f"find number {changes['find_number']} already used", field="find_number"
            )
    for field, value in changes.items():
        setattr(line, field, value)
    stamp_updated(line, actor)
    stamp_updated(line.parent_revision, actor)
    session.flush()
    return get_line(session, line.id)


def remove_line(session: Session, actor: Actor, line: BomLine) -> None:
    components.assert_editable(line.parent_revision)
    parent = line.parent_revision
    # Remove through the relationship so the loaded collection stays accurate; the
    # delete-orphan cascade issues the DELETE on flush.
    parent.bom_lines.remove(line)
    stamp_updated(parent, actor)
    session.flush()


# --- resolution --------------------------------------------------------------------


def _pick_revision(
    component: Component, mode: ResolveMode
) -> tuple[ComponentRevision | None, ResolutionSource]:
    if mode == "released":
        released = component.released_revision
        return (released, "released") if released else (None, "unresolved")
    for rev in reversed(component.revisions):
        if rev.lifecycle_state != LifecycleState.OBSOLETE:
            return rev, "latest"
    return None, "unresolved"


def _build_nodes(
    session: Session,
    revision: ComponentRevision,
    mode: ResolveMode,
    level: int,
    path: tuple[uuid.UUID, ...],
    stats: dict[str, int],
) -> list[BomNode]:
    if level > MAX_DEPTH:
        raise BomCycleError(f"BOM depth exceeds {MAX_DEPTH}; refusing to resolve further")
    nodes: list[BomNode] = []
    lines = sorted(revision.bom_lines, key=lambda line: line.find_number)
    for line in lines:
        child = line.child_component
        if child.id in path:
            raise BomCycleError(
                f"Cycle detected: {child.identifier} appears in its own ancestry",
                component=child.identifier,
            )
        if line.child_revision is not None:
            resolved: ComponentRevision | None = line.child_revision
            source: ResolutionSource = "pinned"
        else:
            resolved, source = _pick_revision(child, mode)
        stats["lines"] += 1
        if resolved is None:
            stats["unresolved"] += 1
        stats["max_depth"] = max(stats["max_depth"], level)
        children: list[BomNode] = []
        if resolved is not None and child.kind == ComponentKind.ASSEMBLY:
            children = _build_nodes(session, resolved, mode, level + 1, (*path, child.id), stats)
        nodes.append(
            BomNode(
                line=BomLineRead.model_validate(line),
                resolved_revision=RevisionSummary.model_validate(resolved) if resolved else None,
                resolution=source,
                level=level,
                children=children,
            )
        )
    return nodes


def resolve_tree(session: Session, revision: ComponentRevision, mode: ResolveMode) -> BomTree:
    _assert_assembly(revision)
    stats = {"lines": 0, "unresolved": 0, "max_depth": 0}
    nodes = _build_nodes(session, revision, mode, 1, (revision.component_id,), stats)
    return BomTree(
        root_component=ComponentSummary.model_validate(revision.component),
        root_revision=RevisionSummary.model_validate(revision),
        mode=mode,
        line_count=stats["lines"],
        unresolved_count=stats["unresolved"],
        max_depth=stats["max_depth"],
        nodes=nodes,
    )


def flatten_tree(tree: BomTree) -> BomFlat:
    rows: list[BomFlatRow] = []

    def walk(nodes: list[BomNode], path: list[str], multiplier: Decimal) -> None:
        for node in nodes:
            extended = node.line.quantity * multiplier
            child_path = [*path, node.line.child_component.identifier]
            rows.append(
                BomFlatRow(
                    level=node.level,
                    path=child_path,
                    find_number=node.line.find_number,
                    component=node.line.child_component,
                    revision=node.resolved_revision,
                    resolution=node.resolution,
                    is_pinned=node.line.is_pinned,
                    quantity=node.line.quantity,
                    extended_quantity=extended,
                    unit=node.line.unit,
                    reference_designator=node.line.reference_designator,
                )
            )
            walk(node.children, child_path, extended)

    walk(tree.nodes, [tree.root_component.identifier], Decimal(1))
    return BomFlat(
        root_component=tree.root_component,
        root_revision=tree.root_revision,
        mode=tree.mode,
        rows=rows,
    )
