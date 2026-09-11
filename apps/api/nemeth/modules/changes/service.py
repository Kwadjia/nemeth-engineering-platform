"""Engineering change rules: identifiers, status flow, evidence links."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from nemeth.core.audit import stamp_created, stamp_updated
from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError, DuplicateIdentifierError, NotFoundError
from nemeth.core.identifiers import next_identifier, normalize_identifier
from nemeth.core.lookup import get_by_ref
from nemeth.core.pagination import PageParams
from nemeth.modules.changes.models import (
    ChangeExperiment,
    ChangeRevision,
    ChangeRole,
    ChangeStatus,
    ChangeTestRun,
    EngineeringChange,
)
from nemeth.modules.changes.schemas import ChangeCreate, ChangeText, ChangeUpdate
from nemeth.modules.components import service as components
from nemeth.modules.components.models import ComponentRevision
from nemeth.modules.experiments import service as experiments
from nemeth.modules.testing import service as testing
from nemeth.modules.testing.models import TestRun

ALLOWED: dict[ChangeStatus, frozenset[ChangeStatus]] = {
    ChangeStatus.DRAFT: frozenset({ChangeStatus.PROPOSED, ChangeStatus.REJECTED}),
    ChangeStatus.PROPOSED: frozenset(
        {ChangeStatus.APPROVED, ChangeStatus.REJECTED, ChangeStatus.DRAFT}
    ),
    ChangeStatus.APPROVED: frozenset({ChangeStatus.IMPLEMENTED, ChangeStatus.REJECTED}),
    ChangeStatus.IMPLEMENTED: frozenset(),
    ChangeStatus.REJECTED: frozenset(),
}
CLOSED = frozenset({ChangeStatus.IMPLEMENTED, ChangeStatus.REJECTED})

_OPTS = (
    selectinload(EngineeringChange.revision_links)
    .selectinload(ChangeRevision.revision)
    .selectinload(ComponentRevision.component),
    selectinload(EngineeringChange.experiment_links).selectinload(ChangeExperiment.experiment),
    selectinload(EngineeringChange.test_run_links)
    .selectinload(ChangeTestRun.test_run)
    .selectinload(TestRun.test_type),
)


def _exists(session: Session, identifier: str) -> bool:
    stmt = (
        select(func.count())
        .select_from(EngineeringChange)
        .where(EngineeringChange.identifier == identifier)
    )
    return bool(session.execute(stmt).scalar_one())


def get_change(session: Session, ref: str) -> EngineeringChange:
    return get_by_ref(session, EngineeringChange, ref, options=_OPTS, label="EngineeringChange")


def list_changes(
    session: Session,
    page: PageParams,
    *,
    q: str | None = None,
    status: ChangeStatus | None = None,
    open_only: bool = False,
) -> tuple[list[EngineeringChange], int]:
    stmt = select(EngineeringChange)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(EngineeringChange.identifier.ilike(pattern), EngineeringChange.title.ilike(pattern))
        )
    if status is not None:
        stmt = stmt.where(EngineeringChange.status == status)
    if open_only:
        stmt = stmt.where(EngineeringChange.status.not_in(list(CLOSED)))
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = (
        stmt.options(*_OPTS)
        .order_by(EngineeringChange.identifier.desc())
        .limit(page.limit)
        .offset(page.offset)
    )
    return list(session.execute(stmt).scalars().unique()), int(total)


def for_revision(session: Session, revision_id: uuid.UUID) -> list[EngineeringChange]:
    stmt = (
        select(EngineeringChange)
        .join(ChangeRevision)
        .where(ChangeRevision.component_revision_id == revision_id)
        .options(*_OPTS)
        .order_by(EngineeringChange.identifier)
        .distinct()
    )
    return list(session.execute(stmt).scalars().unique())


def open_count(session: Session) -> int:
    stmt = (
        select(func.count())
        .select_from(EngineeringChange)
        .where(EngineeringChange.status.not_in(list(CLOSED)))
    )
    return int(session.execute(stmt).scalar_one())


def recent_open(session: Session, limit: int = 5) -> list[EngineeringChange]:
    stmt = (
        select(EngineeringChange)
        .where(EngineeringChange.status.not_in(list(CLOSED)))
        .options(*_OPTS)
        .order_by(EngineeringChange.updated_at.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars().unique())


def _assert_open(change: EngineeringChange) -> None:
    if change.status in CLOSED:
        raise DomainValidationError(
            f"{change.identifier} is {change.status.value}; its links can no longer change.",
            change=change.identifier,
        )


def create_change(session: Session, actor: Actor, data: ChangeCreate) -> EngineeringChange:
    if data.identifier is not None:
        identifier = normalize_identifier(data.identifier)
        if _exists(session, identifier):
            raise DuplicateIdentifierError(
                f"Engineering change {identifier} already exists", identifier=identifier
            )
    else:
        identifier = next_identifier(session, "ECR", exists=lambda c: _exists(session, c), width=4)
    change = EngineeringChange(
        identifier=identifier,
        title=data.title.strip(),
        requested_by=(data.requested_by or actor.display_name).strip(),
        is_placeholder=data.is_placeholder,
        **data.model_dump(include=set(ChangeText.model_fields)),
    )
    stamp_created(change, actor)
    session.add(change)
    session.flush()
    for revision_id in data.affected_revision_ids:
        link_revision(session, actor, change, revision_id, ChangeRole.AFFECTED)
    for revision_id in data.proposed_revision_ids:
        link_revision(session, actor, change, revision_id, ChangeRole.PROPOSED)
    for ref in data.experiment_refs:
        link_experiment(session, actor, change, ref)
    return get_change(session, str(change.id))


def update_change(
    session: Session, actor: Actor, change: EngineeringChange, data: ChangeUpdate
) -> EngineeringChange:
    changes = data.model_dump(exclude_unset=True)
    target = changes.pop("status", None)
    if target is not None and target != change.status:
        if target not in ALLOWED[change.status]:
            allowed = ", ".join(sorted(s.value for s in ALLOWED[change.status])) or "none"
            raise DomainValidationError(
                f"Change cannot move from {change.status.value} to {target.value}. Allowed: {allowed}.",
                field="status",
            )
        if target is ChangeStatus.IMPLEMENTED and not any(
            link.role is ChangeRole.PROPOSED for link in change.revision_links
        ):
            raise DomainValidationError(
                "A change can only be implemented once it names at least one proposed revision.",
                field="status",
            )
        today = datetime.now(tz=UTC).date()
        if target is ChangeStatus.APPROVED:
            changes.setdefault("approved_on", today)
            changes.setdefault("approved_by", actor.display_name)
        if target is ChangeStatus.IMPLEMENTED:
            changes.setdefault("implemented_on", today)
        change.status = target
    for field, value in changes.items():
        if field == "title" and value is None:
            continue
        setattr(change, field, value.strip() if field == "title" else value)
    stamp_updated(change, actor)
    session.flush()
    return change


def link_revision(
    session: Session,
    actor: Actor,
    change: EngineeringChange,
    revision_id: uuid.UUID,
    role: ChangeRole,
) -> EngineeringChange:
    _assert_open(change)
    revision = components.get_revision(session, revision_id)
    if any(
        link.component_revision_id == revision.id and link.role is role
        for link in change.revision_links
    ):
        return change
    link = ChangeRevision(component_revision_id=revision.id, role=role)
    stamp_created(link, actor)
    change.revision_links.append(link)
    stamp_updated(change, actor)
    session.flush()
    return get_change(session, str(change.id))


def unlink_revision(
    session: Session,
    actor: Actor,
    change: EngineeringChange,
    revision_id: uuid.UUID,
    role: ChangeRole,
) -> None:
    _assert_open(change)
    link = next(
        (
            x
            for x in change.revision_links
            if x.component_revision_id == revision_id and x.role is role
        ),
        None,
    )
    if link is None:
        raise NotFoundError(f"Revision {revision_id} is not linked as {role.value}")
    change.revision_links.remove(link)
    stamp_updated(change, actor)
    session.flush()


def link_experiment(
    session: Session, actor: Actor, change: EngineeringChange, ref: str
) -> EngineeringChange:
    _assert_open(change)
    experiment = experiments.get_experiment(session, ref)
    if any(x.experiment_id == experiment.id for x in change.experiment_links):
        return change
    link = ChangeExperiment(experiment_id=experiment.id)
    stamp_created(link, actor)
    change.experiment_links.append(link)
    stamp_updated(change, actor)
    session.flush()
    return get_change(session, str(change.id))


def unlink_experiment(session: Session, actor: Actor, change: EngineeringChange, ref: str) -> None:
    _assert_open(change)
    experiment = experiments.get_experiment(session, ref)
    link = next((x for x in change.experiment_links if x.experiment_id == experiment.id), None)
    if link is None:
        raise NotFoundError(f"{experiment.identifier} is not linked to {change.identifier}")
    change.experiment_links.remove(link)
    stamp_updated(change, actor)
    session.flush()


def link_test_run(
    session: Session, actor: Actor, change: EngineeringChange, ref: str
) -> EngineeringChange:
    _assert_open(change)
    run = testing.get_test_run(session, ref)
    if any(x.test_run_id == run.id for x in change.test_run_links):
        return change
    link = ChangeTestRun(test_run_id=run.id)
    stamp_created(link, actor)
    change.test_run_links.append(link)
    stamp_updated(change, actor)
    session.flush()
    return get_change(session, str(change.id))


def unlink_test_run(session: Session, actor: Actor, change: EngineeringChange, ref: str) -> None:
    _assert_open(change)
    run = testing.get_test_run(session, ref)
    link = next((x for x in change.test_run_links if x.test_run_id == run.id), None)
    if link is None:
        raise NotFoundError(f"{run.identifier} is not linked to {change.identifier}")
    change.test_run_links.remove(link)
    stamp_updated(change, actor)
    session.flush()
