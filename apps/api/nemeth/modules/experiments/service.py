"""Experiment rules: identifiers, status flow, links to prototypes and revisions."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from nemeth.core.audit import stamp_created, stamp_updated
from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError, DuplicateIdentifierError, NotFoundError
from nemeth.core.identifiers import next_identifier, normalize_identifier
from nemeth.core.lookup import get_by_ref
from nemeth.core.pagination import PageParams
from nemeth.modules.components import service as components
from nemeth.modules.components.models import ComponentRevision
from nemeth.modules.experiments.models import (
    Experiment,
    ExperimentPrototype,
    ExperimentRevision,
    ExperimentStatus,
)
from nemeth.modules.experiments.schemas import (
    ExperimentCreate,
    ExperimentText,
    ExperimentUpdate,
    LinkPrototype,
    LinkRevision,
)
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.models import Prototype

ALLOWED: dict[ExperimentStatus, frozenset[ExperimentStatus]] = {
    ExperimentStatus.PLANNED: frozenset({ExperimentStatus.IN_PROGRESS, ExperimentStatus.ABANDONED}),
    ExperimentStatus.IN_PROGRESS: frozenset(
        {ExperimentStatus.COMPLETED, ExperimentStatus.ABANDONED}
    ),
    ExperimentStatus.COMPLETED: frozenset(),
    ExperimentStatus.ABANDONED: frozenset(),
}

_OPTS = (
    selectinload(Experiment.prototype_links).selectinload(ExperimentPrototype.prototype),
    selectinload(Experiment.revision_links)
    .selectinload(ExperimentRevision.revision)
    .selectinload(ComponentRevision.component),
)


def _exists(session: Session, identifier: str) -> bool:
    stmt = select(func.count()).select_from(Experiment).where(Experiment.identifier == identifier)
    return bool(session.execute(stmt).scalar_one())


def get_experiment(session: Session, ref: str) -> Experiment:
    return get_by_ref(session, Experiment, ref, options=_OPTS, label="Experiment")


def list_experiments(
    session: Session,
    page: PageParams,
    *,
    q: str | None = None,
    status: ExperimentStatus | None = None,
    prototype_id: uuid.UUID | None = None,
) -> tuple[list[Experiment], int]:
    stmt = select(Experiment)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Experiment.identifier.ilike(pattern), Experiment.title.ilike(pattern))
        )
    if status is not None:
        stmt = stmt.where(Experiment.status == status)
    if prototype_id is not None:
        stmt = stmt.join(ExperimentPrototype).where(
            ExperimentPrototype.prototype_id == prototype_id
        )
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = (
        stmt.options(*_OPTS)
        .order_by(Experiment.identifier.desc())
        .limit(page.limit)
        .offset(page.offset)
    )
    return list(session.execute(stmt).scalars().unique()), int(total)


def recent(session: Session, limit: int = 5) -> list[Experiment]:
    stmt = select(Experiment).options(*_OPTS).order_by(Experiment.updated_at.desc()).limit(limit)
    return list(session.execute(stmt).scalars().unique())


def for_revision(session: Session, revision_id: uuid.UUID) -> list[Experiment]:
    stmt = (
        select(Experiment)
        .join(ExperimentRevision)
        .where(ExperimentRevision.component_revision_id == revision_id)
        .options(*_OPTS)
        .order_by(Experiment.identifier)
    )
    return list(session.execute(stmt).scalars().unique())


def _assert_move(current: ExperimentStatus, target: ExperimentStatus) -> None:
    if target not in ALLOWED[current]:
        allowed = ", ".join(sorted(s.value for s in ALLOWED[current])) or "none"
        raise DomainValidationError(
            f"Experiment cannot move from {current.value} to {target.value}. Allowed: {allowed}.",
            field="status",
        )


def create_experiment(session: Session, actor: Actor, data: ExperimentCreate) -> Experiment:
    if data.identifier is not None:
        identifier = normalize_identifier(data.identifier)
        if _exists(session, identifier):
            raise DuplicateIdentifierError(
                f"Experiment {identifier} already exists", identifier=identifier
            )
    else:
        identifier = next_identifier(session, "EXP", exists=lambda c: _exists(session, c))
    experiment = Experiment(
        identifier=identifier,
        title=data.title.strip(),
        status=data.status,
        started_on=data.started_on,
        is_placeholder=data.is_placeholder,
        **data.model_dump(include=set(ExperimentText.model_fields)),
    )
    stamp_created(experiment, actor)
    session.add(experiment)
    session.flush()
    for prototype_id in data.prototype_ids:
        link_prototype(session, actor, experiment, LinkPrototype(prototype_id=prototype_id))
    return get_experiment(session, str(experiment.id))


def update_experiment(
    session: Session, actor: Actor, experiment: Experiment, data: ExperimentUpdate
) -> Experiment:
    changes = data.model_dump(exclude_unset=True)
    target = changes.pop("status", None)
    if target is not None and target != experiment.status:
        _assert_move(experiment.status, target)
        experiment.status = target
        if target is ExperimentStatus.COMPLETED and experiment.completed_on is None:
            changes.setdefault("completed_on", None)
    for field, value in changes.items():
        if field == "title" and value is None:
            continue
        setattr(experiment, field, value.strip() if field == "title" else value)
    stamp_updated(experiment, actor)
    session.flush()
    return experiment


def link_prototype(
    session: Session, actor: Actor, experiment: Experiment, data: LinkPrototype
) -> Experiment:
    if data.prototype_id is not None:
        prototype = prototypes.get_prototype(session, str(data.prototype_id))
    elif data.prototype_identifier is not None:
        prototype = prototypes.get_prototype(session, data.prototype_identifier)
    else:
        raise DomainValidationError("prototype_id or prototype_identifier is required")
    if any(link.prototype_id == prototype.id for link in experiment.prototype_links):
        return experiment
    link = ExperimentPrototype(prototype_id=prototype.id, role=data.role)
    stamp_created(link, actor)
    experiment.prototype_links.append(link)
    stamp_updated(experiment, actor)
    session.flush()
    return get_experiment(session, str(experiment.id))


def unlink_prototype(
    session: Session, actor: Actor, experiment: Experiment, prototype: Prototype
) -> None:
    link = next((x for x in experiment.prototype_links if x.prototype_id == prototype.id), None)
    if link is None:
        raise NotFoundError(f"{prototype.identifier} is not linked to {experiment.identifier}")
    experiment.prototype_links.remove(link)
    stamp_updated(experiment, actor)
    session.flush()


def link_revision(
    session: Session, actor: Actor, experiment: Experiment, data: LinkRevision
) -> Experiment:
    revision = components.get_revision(session, data.component_revision_id)
    if any(link.component_revision_id == revision.id for link in experiment.revision_links):
        return experiment
    link = ExperimentRevision(component_revision_id=revision.id, role=data.role)
    stamp_created(link, actor)
    experiment.revision_links.append(link)
    stamp_updated(experiment, actor)
    session.flush()
    return get_experiment(session, str(experiment.id))


def unlink_revision(
    session: Session, actor: Actor, experiment: Experiment, revision_id: uuid.UUID
) -> None:
    link = next(
        (x for x in experiment.revision_links if x.component_revision_id == revision_id), None
    )
    if link is None:
        raise NotFoundError(f"Revision {revision_id} is not linked to {experiment.identifier}")
    experiment.revision_links.remove(link)
    stamp_updated(experiment, actor)
    session.flush()


def count_by_status(session: Session) -> dict[str, int]:
    stmt = select(Experiment.status, func.count()).group_by(Experiment.status)
    counts = {s.value: 0 for s in ExperimentStatus}
    for status, count in session.execute(stmt).all():
        counts[ExperimentStatus(status).value] = int(count)
    return counts
