"""Watch register rules and the dossier (digital build record)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from nemeth.core.audit import stamp_created, stamp_updated
from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError, DuplicateIdentifierError
from nemeth.core.identifiers import next_identifier, normalize_identifier
from nemeth.core.lookup import get_by_ref
from nemeth.core.pagination import PageParams
from nemeth.modules.products import service as products
from nemeth.modules.products.models import ProductModel
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.watches.models import Watch, WatchStatus
from nemeth.modules.watches.schemas import WatchCreate, WatchUpdate

_OPTS = (
    selectinload(Watch.product_model).selectinload(ProductModel.product),
    selectinload(Watch.product_model).selectinload(ProductModel.caliber),
    selectinload(Watch.origin_prototype),
    selectinload(Watch.current_instances),
    selectinload(Watch.build_records),
)

#: PLANNED → IN_BUILD → BUILT, then the "in the world" states move freely among
#: themselves; RETIRED is terminal.
ALLOWED: dict[WatchStatus, frozenset[WatchStatus]] = {
    WatchStatus.PLANNED: frozenset({WatchStatus.IN_BUILD, WatchStatus.RETIRED}),
    WatchStatus.IN_BUILD: frozenset({WatchStatus.BUILT, WatchStatus.RETIRED}),
    WatchStatus.BUILT: frozenset(
        {
            WatchStatus.PERSONAL_PROTOTYPE,
            WatchStatus.DELIVERED,
            WatchStatus.IN_SERVICE,
            WatchStatus.RETIRED,
        }
    ),
    WatchStatus.PERSONAL_PROTOTYPE: frozenset(
        {WatchStatus.DELIVERED, WatchStatus.IN_SERVICE, WatchStatus.RETIRED}
    ),
    WatchStatus.DELIVERED: frozenset(
        {WatchStatus.IN_SERVICE, WatchStatus.PERSONAL_PROTOTYPE, WatchStatus.RETIRED}
    ),
    WatchStatus.IN_SERVICE: frozenset(
        {WatchStatus.DELIVERED, WatchStatus.PERSONAL_PROTOTYPE, WatchStatus.RETIRED}
    ),
    WatchStatus.RETIRED: frozenset(),
}


def _exists(session: Session, identifier: str) -> bool:
    stmt = select(func.count()).select_from(Watch).where(Watch.identifier == identifier)
    return bool(session.execute(stmt).scalar_one())


def get_watch(session: Session, ref: str) -> Watch:
    return get_by_ref(session, Watch, ref, options=_OPTS, label="Watch")


def list_watches(
    session: Session, page: PageParams, *, status: WatchStatus | None = None
) -> tuple[list[Watch], int]:
    stmt = select(Watch)
    if status is not None:
        stmt = stmt.where(Watch.status == status)
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = stmt.options(*_OPTS).order_by(Watch.identifier).limit(page.limit).offset(page.offset)
    return list(session.execute(stmt).scalars().unique()), int(total)


def count(session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(Watch)).scalar_one())


def _serial_from(identifier: str) -> str:
    match = re.search(r"(\d+)$", identifier)
    if not match:
        raise DomainValidationError(
            "A watch identifier must end in the serial number, e.g. N1-017",
            field="identifier",
        )
    return match.group(1)


def create_watch(session: Session, actor: Actor, data: WatchCreate) -> Watch:
    model = products.get_model(session, data.product_model_ref)
    product_code = model.product.identifier
    if data.identifier is not None:
        identifier = normalize_identifier(data.identifier)
        if _exists(session, identifier):
            raise DuplicateIdentifierError(
                f"Watch {identifier} already exists", identifier=identifier
            )
    else:
        identifier = next_identifier(session, product_code, exists=lambda c: _exists(session, c))
    origin = (
        prototypes.get_prototype(session, data.origin_prototype_ref)
        if data.origin_prototype_ref
        else None
    )
    watch = Watch(
        identifier=identifier,
        serial_number=data.serial_number or _serial_from(identifier),
        product_model_id=model.id,
        status=data.status,
        owner_name=data.owner_name,
        origin_prototype_id=origin.id if origin else None,
        assembled_on=data.assembled_on,
        delivered_on=data.delivered_on,
        notes=data.notes,
        is_placeholder=data.is_placeholder,
    )
    stamp_created(watch, actor)
    session.add(watch)
    session.flush()
    return get_watch(session, str(watch.id))


def update_watch(session: Session, actor: Actor, watch: Watch, data: WatchUpdate) -> Watch:
    changes = data.model_dump(exclude_unset=True)
    target = changes.pop("status", None)
    if target is not None and target != watch.status:
        if target not in ALLOWED[watch.status]:
            allowed = ", ".join(sorted(s.value for s in ALLOWED[watch.status])) or "none"
            raise DomainValidationError(
                f"Watch cannot move from {watch.status.value} to {target.value}. Allowed: {allowed}.",
                field="status",
            )
        watch.status = target
    origin_ref = changes.pop("origin_prototype_ref", None)
    if origin_ref is not None:
        watch.origin_prototype_id = prototypes.get_prototype(session, origin_ref).id
    for field, value in changes.items():
        setattr(watch, field, value)
    stamp_updated(watch, actor)
    session.flush()
    session.expire(watch)
    return get_watch(session, str(watch.id))


def by_model(session: Session, model_id: uuid.UUID) -> list[Watch]:
    stmt = (
        select(Watch)
        .where(Watch.product_model_id == model_id)
        .options(*_OPTS)
        .order_by(Watch.identifier)
    )
    return list(session.execute(stmt).scalars().unique())
