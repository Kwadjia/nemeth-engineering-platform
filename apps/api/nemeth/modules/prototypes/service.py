"""Prototype, part-instance and build-record rules (ADR-008)."""

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
from nemeth.modules.components.models import Component, ComponentRevision
from nemeth.modules.components.schemas import ComponentSummary, RevisionSummary
from nemeth.modules.products.models import Caliber, ProductModel
from nemeth.modules.prototypes.models import (
    BuildAction,
    BuildEntry,
    BuildRecord,
    PartInstance,
    PartInstanceStatus,
    Prototype,
    PrototypeStatus,
)
from nemeth.modules.prototypes.schemas import (
    BuildRecordCreate,
    BuildRecordSummary,
    BuildRecordUpdate,
    ConfigurationRow,
    PartInstanceCreate,
    PartInstanceSummary,
    PartInstanceUpdate,
    PrototypeConfiguration,
    PrototypeCreate,
    PrototypeSummary,
    PrototypeUpdate,
)

PROTOTYPE_ORDER: tuple[PrototypeStatus, ...] = (
    PrototypeStatus.PLANNED,
    PrototypeStatus.BUILDING,
    PrototypeStatus.ACTIVE,
    PrototypeStatus.RETIRED,
)

_PROTOTYPE_OPTS = (
    selectinload(Prototype.product_model),
    selectinload(Prototype.caliber),
    selectinload(Prototype.current_instances),
    selectinload(Prototype.build_records),
)
_INSTANCE_OPTS = (
    selectinload(PartInstance.revision).selectinload(ComponentRevision.component),
    selectinload(PartInstance.current_prototype),
)
_BUILD_OPTS = (
    selectinload(BuildRecord.prototype),
    selectinload(BuildRecord.entries)
    .selectinload(BuildEntry.part_instance)
    .selectinload(PartInstance.revision)
    .selectinload(ComponentRevision.component),
)


# --- prototypes --------------------------------------------------------------------


def _prototype_identifier_exists(session: Session, identifier: str) -> bool:
    stmt = select(func.count()).select_from(Prototype).where(Prototype.identifier == identifier)
    return bool(session.execute(stmt).scalar_one())


def list_prototypes(
    session: Session, page: PageParams, status: PrototypeStatus | None = None
) -> tuple[list[Prototype], int]:
    stmt = select(Prototype)
    if status is not None:
        stmt = stmt.where(Prototype.status == status)
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = (
        stmt.options(*_PROTOTYPE_OPTS)
        .order_by(Prototype.identifier)
        .limit(page.limit)
        .offset(page.offset)
    )
    return list(session.execute(stmt).scalars().unique()), int(total)


def get_prototype(session: Session, ref: str) -> Prototype:
    return get_by_ref(session, Prototype, ref, options=_PROTOTYPE_OPTS, label="Prototype")


def active_prototype(session: Session) -> Prototype | None:
    stmt = (
        select(Prototype)
        .where(Prototype.status.in_([PrototypeStatus.ACTIVE, PrototypeStatus.BUILDING]))
        .options(*_PROTOTYPE_OPTS)
        .order_by(Prototype.updated_at.desc())
        .limit(1)
    )
    return session.execute(stmt).scalars().unique().first()


def _assert_status_move(current: PrototypeStatus, target: PrototypeStatus) -> None:
    if PROTOTYPE_ORDER.index(target) < PROTOTYPE_ORDER.index(current):
        raise DomainValidationError(
            f"Prototype status cannot move backwards from {current.value} to {target.value}",
            field="status",
        )


def _validate_links(
    session: Session, model_id: uuid.UUID | None, caliber_id: uuid.UUID | None
) -> None:
    if model_id is not None:
        get_by_ref(session, ProductModel, str(model_id), label="ProductModel")
    if caliber_id is not None:
        get_by_ref(session, Caliber, str(caliber_id), label="Caliber")


def create_prototype(session: Session, actor: Actor, data: PrototypeCreate) -> Prototype:
    if data.identifier is not None:
        identifier = normalize_identifier(data.identifier)
        if _prototype_identifier_exists(session, identifier):
            raise DuplicateIdentifierError(
                f"Prototype {identifier} already exists", identifier=identifier
            )
    else:
        assert data.product_code is not None
        prefix = f"{normalize_identifier(data.product_code)}-P"
        identifier = next_identifier(
            session,
            prefix,
            exists=lambda c: _prototype_identifier_exists(session, c),
            separator="",
        )
    _validate_links(session, data.product_model_id, data.caliber_id)
    prototype = Prototype(
        identifier=identifier,
        name=data.name.strip(),
        purpose=data.purpose,
        status=data.status,
        product_model_id=data.product_model_id,
        caliber_id=data.caliber_id,
        started_on=data.started_on,
        notes=data.notes,
        is_placeholder=data.is_placeholder,
    )
    stamp_created(prototype, actor)
    session.add(prototype)
    session.flush()
    return get_prototype(session, str(prototype.id))


def update_prototype(
    session: Session, actor: Actor, prototype: Prototype, data: PrototypeUpdate
) -> Prototype:
    changes = data.model_dump(exclude_unset=True)
    target = changes.pop("status", None)
    if target is not None and target != prototype.status:
        _assert_status_move(prototype.status, target)
        prototype.status = target
    _validate_links(session, changes.get("product_model_id"), changes.get("caliber_id"))
    for field, value in changes.items():
        if field == "name" and value is None:
            continue
        setattr(prototype, field, value.strip() if field == "name" else value)
    stamp_updated(prototype, actor)
    session.flush()
    session.expire(prototype)
    return get_prototype(session, str(prototype.id))


# --- part instances ----------------------------------------------------------------


def _instance_identifier_exists(session: Session, identifier: str) -> bool:
    stmt = (
        select(func.count()).select_from(PartInstance).where(PartInstance.identifier == identifier)
    )
    return bool(session.execute(stmt).scalar_one())


def get_part_instance(session: Session, ref: str) -> PartInstance:
    return get_by_ref(session, PartInstance, ref, options=_INSTANCE_OPTS, label="PartInstance")


def list_part_instances(
    session: Session,
    page: PageParams,
    *,
    q: str | None = None,
    status: PartInstanceStatus | None = None,
    component_id: uuid.UUID | None = None,
    prototype_id: uuid.UUID | None = None,
) -> tuple[list[PartInstance], int]:
    stmt = select(PartInstance).join(
        ComponentRevision, PartInstance.component_revision_id == ComponentRevision.id
    )
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.join(Component, ComponentRevision.component_id == Component.id).where(
            or_(
                PartInstance.identifier.ilike(pattern),
                PartInstance.serial_number.ilike(pattern),
                Component.identifier.ilike(pattern),
                Component.name.ilike(pattern),
            )
        )
    if status is not None:
        stmt = stmt.where(PartInstance.status == status)
    if component_id is not None:
        stmt = stmt.where(ComponentRevision.component_id == component_id)
    if prototype_id is not None:
        stmt = stmt.where(PartInstance.current_prototype_id == prototype_id)
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = (
        stmt.options(*_INSTANCE_OPTS)
        .order_by(PartInstance.identifier)
        .limit(page.limit)
        .offset(page.offset)
    )
    return list(session.execute(stmt).scalars().unique()), int(total)


def instances_for_component(session: Session, component: Component) -> list[PartInstance]:
    stmt = (
        select(PartInstance)
        .join(ComponentRevision, PartInstance.component_revision_id == ComponentRevision.id)
        .where(ComponentRevision.component_id == component.id)
        .options(*_INSTANCE_OPTS)
        .order_by(PartInstance.identifier)
    )
    return list(session.execute(stmt).scalars().unique())


def create_part_instances(
    session: Session, actor: Actor, data: PartInstanceCreate
) -> list[PartInstance]:
    revision = components.get_revision(session, data.component_revision_id)
    if not revision.is_frozen:
        raise DomainValidationError(
            f"{revision.display_identifier} is {revision.lifecycle_state.value}. Physical parts "
            "can only be recorded against frozen revisions (PROTOTYPE or later); transition the "
            "revision first.",
            field="component_revision_id",
            revision=revision.display_identifier,
        )
    created: list[PartInstance] = []
    for _ in range(data.quantity):
        identifier = next_identifier(
            session, "PI", exists=lambda c: _instance_identifier_exists(session, c), width=5
        )
        instance = PartInstance(
            identifier=identifier,
            component_revision_id=revision.id,
            serial_number=data.serial_number if data.quantity == 1 else None,
            lot=data.lot,
            source=data.source,
            material_lot=data.material_lot,
            heat_treatment_lot=data.heat_treatment_lot,
            supplier_note=data.supplier_note,
            notes=data.notes,
            is_placeholder=data.is_placeholder,
        )
        stamp_created(instance, actor)
        session.add(instance)
        created.append(instance)
    session.flush()
    return [get_part_instance(session, str(i.id)) for i in created]


def update_part_instance(
    session: Session, actor: Actor, instance: PartInstance, data: PartInstanceUpdate
) -> PartInstance:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(instance, field, value)
    stamp_updated(instance, actor)
    session.flush()
    return instance


# --- build records -----------------------------------------------------------------


def _build_identifier_exists(session: Session, identifier: str) -> bool:
    stmt = select(func.count()).select_from(BuildRecord).where(BuildRecord.identifier == identifier)
    return bool(session.execute(stmt).scalar_one())


def get_build_record(session: Session, ref: str) -> BuildRecord:
    return get_by_ref(session, BuildRecord, ref, options=_BUILD_OPTS, label="BuildRecord")


def list_build_records(session: Session, prototype: Prototype) -> list[BuildRecord]:
    stmt = (
        select(BuildRecord)
        .where(BuildRecord.prototype_id == prototype.id)
        .options(*_BUILD_OPTS)
        .order_by(BuildRecord.performed_on.desc(), BuildRecord.created_at.desc())
    )
    return list(session.execute(stmt).scalars().unique())


def _resolve_instance(
    session: Session, instance_id: uuid.UUID | None, identifier: str | None
) -> PartInstance:
    if instance_id is not None:
        return get_part_instance(session, str(instance_id))
    assert identifier is not None
    return get_part_instance(session, identifier)


def create_build_record(
    session: Session, actor: Actor, prototype: Prototype, data: BuildRecordCreate
) -> BuildRecord:
    if prototype.status == PrototypeStatus.RETIRED:
        raise DomainValidationError(
            f"{prototype.identifier} is retired; no further build records can be added.",
            prototype=prototype.identifier,
        )
    identifier = next_identifier(
        session, "BR", exists=lambda c: _build_identifier_exists(session, c), width=5
    )
    record = BuildRecord(
        identifier=identifier,
        prototype_id=prototype.id,
        title=data.title.strip(),
        performed_on=data.performed_on,
        performed_by=(data.performed_by or actor.display_name).strip(),
        procedure=data.procedure,
        notes=data.notes,
    )
    stamp_created(record, actor)
    session.add(record)
    session.flush()

    seen: set[uuid.UUID] = set()
    for sequence, entry in enumerate(data.entries, start=1):
        instance = _resolve_instance(
            session, entry.part_instance_id, entry.part_instance_identifier
        )
        if instance.id in seen:
            raise DomainValidationError(
                f"{instance.identifier} appears more than once in this build record",
                field="entries",
            )
        seen.add(instance.id)

        if entry.action is BuildAction.INSTALL:
            if instance.status is PartInstanceStatus.SCRAPPED:
                raise DomainValidationError(
                    f"{instance.identifier} is scrapped and cannot be installed", field="entries"
                )
            if instance.current_prototype_id is not None:
                where = (
                    instance.current_prototype.identifier
                    if instance.current_prototype
                    else "another unit"
                )
                raise DomainValidationError(
                    f"{instance.identifier} is already installed in {where}; remove it first",
                    field="entries",
                    part_instance=instance.identifier,
                )
            instance.status = PartInstanceStatus.INSTALLED
            instance.current_prototype = prototype
            instance.current_prototype_id = prototype.id
        else:
            if instance.current_prototype_id != prototype.id:
                raise DomainValidationError(
                    f"{instance.identifier} is not installed in {prototype.identifier}",
                    field="entries",
                    part_instance=instance.identifier,
                )
            instance.status = PartInstanceStatus.REMOVED
            instance.current_prototype = None
            instance.current_prototype_id = None
        stamp_updated(instance, actor)

        row = BuildEntry(
            sequence=sequence,
            action=entry.action,
            position=entry.position,
            notes=entry.notes,
            part_instance_id=instance.id,
        )
        stamp_created(row, actor)
        record.entries.append(row)

    if prototype.status is PrototypeStatus.PLANNED and data.entries:
        prototype.status = PrototypeStatus.BUILDING
    stamp_updated(prototype, actor)
    session.flush()
    session.expire(prototype)
    return get_build_record(session, str(record.id))


def update_build_record(
    session: Session, actor: Actor, record: BuildRecord, data: BuildRecordUpdate
) -> BuildRecord:
    """Build records are history; only free-text notes may change."""
    changes = data.model_dump(exclude_unset=True)
    if "notes" in changes:
        record.notes = changes["notes"]
    stamp_updated(record, actor)
    session.flush()
    return record


# --- configuration -----------------------------------------------------------------


def _last_install(session: Session, instance: PartInstance) -> BuildEntry | None:
    stmt = (
        select(BuildEntry)
        .join(BuildRecord, BuildEntry.build_record_id == BuildRecord.id)
        .where(
            BuildEntry.part_instance_id == instance.id,
            BuildEntry.action == BuildAction.INSTALL,
            BuildRecord.prototype_id == instance.current_prototype_id,
        )
        .options(selectinload(BuildEntry.build_record))
        .order_by(
            BuildRecord.performed_on.desc(),
            BuildRecord.created_at.desc(),
            BuildEntry.sequence.desc(),
        )
        .limit(1)
    )
    return session.execute(stmt).scalars().first()


def configuration(session: Session, prototype: Prototype) -> PrototypeConfiguration:
    """Every part instance currently installed, with its exact revision (ADR-008)."""
    stmt = (
        select(PartInstance)
        .join(ComponentRevision, PartInstance.component_revision_id == ComponentRevision.id)
        .join(Component, ComponentRevision.component_id == Component.id)
        .where(PartInstance.current_prototype_id == prototype.id)
        .options(*_INSTANCE_OPTS)
        .order_by(Component.identifier, PartInstance.identifier)
    )
    rows: list[ConfigurationRow] = []
    for instance in session.execute(stmt).scalars().unique():
        entry = _last_install(session, instance)
        rows.append(
            ConfigurationRow(
                part_instance=PartInstanceSummary.model_validate(instance),
                component=ComponentSummary.model_validate(instance.component),
                revision=RevisionSummary.model_validate(instance.revision),
                position=entry.position if entry else None,
                installed_by=(
                    BuildRecordSummary.model_validate(entry.build_record) if entry else None
                ),
            )
        )
    return PrototypeConfiguration(
        prototype=PrototypeSummary.model_validate(prototype), count=len(rows), rows=rows
    )


def prototypes_containing_revision(session: Session, revision_id: uuid.UUID) -> list[Prototype]:
    stmt = (
        select(Prototype)
        .join(PartInstance, PartInstance.current_prototype_id == Prototype.id)
        .where(PartInstance.component_revision_id == revision_id)
        .options(*_PROTOTYPE_OPTS)
        .order_by(Prototype.identifier)
        .distinct()
    )
    return list(session.execute(stmt).scalars().unique())


def prototype_count(session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(Prototype)).scalar_one())


def ensure_exists(session: Session, prototype_id: uuid.UUID) -> Prototype:
    prototype = session.get(Prototype, prototype_id)
    if prototype is None:
        raise NotFoundError(f"Prototype {prototype_id} not found", resource="Prototype")
    return prototype
