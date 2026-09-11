from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.db import get_session
from nemeth.core.pagination import Page, PageParams, page_params
from nemeth.modules.components.schemas import RevisionRead
from nemeth.modules.prototypes.schemas import PartInstanceRead
from nemeth.modules.suppliers import service
from nemeth.modules.suppliers.models import SupplierKind
from nemeth.modules.suppliers.schemas import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter(tags=["suppliers"])


@router.get("/suppliers", response_model=Page[SupplierRead])
def list_suppliers(
    q: str | None = Query(default=None),
    kind: SupplierKind | None = None,
    include_inactive: bool = True,
    page: PageParams = Depends(page_params),
    session: Session = Depends(get_session),
) -> Page[SupplierRead]:
    items, total = service.list_suppliers(
        session, page, q=q, kind=kind, include_inactive=include_inactive
    )
    return Page(
        items=[SupplierRead.model_validate(s) for s in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("/suppliers", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> SupplierRead:
    return SupplierRead.model_validate(service.create_supplier(session, actor, payload))


@router.get("/suppliers/{ref}", response_model=SupplierRead)
def get_supplier(ref: str, session: Session = Depends(get_session)) -> SupplierRead:
    return SupplierRead.model_validate(service.get_supplier(session, ref))


@router.patch("/suppliers/{ref}", response_model=SupplierRead)
def update_supplier(
    ref: str,
    payload: SupplierUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> SupplierRead:
    supplier = service.get_supplier(session, ref)
    return SupplierRead.model_validate(service.update_supplier(session, actor, supplier, payload))


@router.get("/suppliers/{ref}/revisions", response_model=list[RevisionRead])
def supplier_revisions(ref: str, session: Session = Depends(get_session)) -> list[RevisionRead]:
    """Component revisions that name this supplier as their default source."""
    supplier = service.get_supplier(session, ref)
    return [RevisionRead.model_validate(r) for r in service.revisions_for(session, supplier)]


@router.get("/suppliers/{ref}/part-instances", response_model=list[PartInstanceRead])
def supplier_part_instances(
    ref: str, session: Session = Depends(get_session)
) -> list[PartInstanceRead]:
    """Physical parts actually sourced from this supplier."""
    supplier = service.get_supplier(session, ref)
    return [
        PartInstanceRead.model_validate(i) for i in service.part_instances_for(session, supplier)
    ]
