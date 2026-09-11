from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from nemeth.core.audit import stamp_created, stamp_updated
from nemeth.core.auth import Actor
from nemeth.core.errors import DuplicateIdentifierError, NotFoundError
from nemeth.core.identifiers import next_identifier, normalize_identifier
from nemeth.core.lookup import get_by_ref
from nemeth.core.pagination import PageParams
from nemeth.modules.suppliers.models import Supplier, SupplierKind
from nemeth.modules.suppliers.schemas import SupplierCreate, SupplierUpdate

if TYPE_CHECKING:
    from nemeth.modules.components.models import ComponentRevision
    from nemeth.modules.prototypes.models import PartInstance


def _exists(session: Session, identifier: str) -> bool:
    stmt = select(func.count()).select_from(Supplier).where(Supplier.identifier == identifier)
    return bool(session.execute(stmt).scalar_one())


def get_supplier(session: Session, ref: str) -> Supplier:
    return get_by_ref(session, Supplier, ref, label="Supplier")


def require_supplier(session: Session, supplier_id: uuid.UUID | None) -> Supplier | None:
    if supplier_id is None:
        return None
    supplier = session.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFoundError(f"Supplier {supplier_id} not found", resource="Supplier")
    return supplier


def list_suppliers(
    session: Session,
    page: PageParams,
    *,
    q: str | None = None,
    kind: SupplierKind | None = None,
    include_inactive: bool = True,
) -> tuple[list[Supplier], int]:
    stmt = select(Supplier)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Supplier.identifier.ilike(pattern),
                Supplier.name.ilike(pattern),
                Supplier.capabilities.ilike(pattern),
            )
        )
    if kind is not None:
        stmt = stmt.where(Supplier.kind == kind)
    if not include_inactive:
        stmt = stmt.where(Supplier.is_active.is_(True))
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = stmt.order_by(Supplier.name).limit(page.limit).offset(page.offset)
    return list(session.execute(stmt).scalars()), int(total)


def create_supplier(session: Session, actor: Actor, data: SupplierCreate) -> Supplier:
    if data.identifier is not None:
        identifier = normalize_identifier(data.identifier)
        if _exists(session, identifier):
            raise DuplicateIdentifierError(
                f"Supplier {identifier} already exists", identifier=identifier
            )
    else:
        identifier = next_identifier(session, "SUP", exists=lambda c: _exists(session, c))
    supplier = Supplier(identifier=identifier, **data.model_dump(exclude={"identifier"}))
    supplier.name = data.name.strip()
    stamp_created(supplier, actor)
    session.add(supplier)
    session.flush()
    return supplier


def update_supplier(
    session: Session, actor: Actor, supplier: Supplier, data: SupplierUpdate
) -> Supplier:
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field in ("name", "kind", "is_active", "is_placeholder"):
            continue
        setattr(supplier, field, value.strip() if field == "name" else value)
    stamp_updated(supplier, actor)
    session.flush()
    return supplier


def revisions_for(session: Session, supplier: Supplier) -> list[ComponentRevision]:
    # Imported here: the prototype/watch mappers must not be configured while the
    # components module is still importing (see docs/development/conventions.md).
    from nemeth.modules.components.models import ComponentRevision

    stmt = (
        select(ComponentRevision)
        .where(ComponentRevision.supplier_id == supplier.id)
        .options(selectinload(ComponentRevision.component))
        .order_by(ComponentRevision.created_at.desc())
    )
    return list(session.execute(stmt).scalars())


def part_instances_for(session: Session, supplier: Supplier) -> list[PartInstance]:
    from nemeth.modules.components.models import ComponentRevision
    from nemeth.modules.prototypes.models import PartInstance

    stmt = (
        select(PartInstance)
        .where(PartInstance.supplier_id == supplier.id)
        .options(
            selectinload(PartInstance.revision).selectinload(ComponentRevision.component),
            selectinload(PartInstance.current_prototype),
            selectinload(PartInstance.current_watch),
        )
        .order_by(PartInstance.identifier)
    )
    return list(session.execute(stmt).scalars())


def count(session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(Supplier)).scalar_one())
