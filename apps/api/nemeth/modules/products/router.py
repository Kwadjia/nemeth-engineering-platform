from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor, get_actor
from nemeth.core.db import get_session
from nemeth.core.errors import NotFoundError
from nemeth.core.pagination import Page, PageParams, page_params
from nemeth.modules.bom import service as bom
from nemeth.modules.bom.schemas import BomTree, ResolveMode
from nemeth.modules.components import service as components
from nemeth.modules.components.models import Component
from nemeth.modules.products import service
from nemeth.modules.products.schemas import (
    CaliberCreate,
    CaliberRead,
    CaliberUpdate,
    ProductCreate,
    ProductModelCreate,
    ProductModelRead,
    ProductModelUpdate,
    ProductRead,
    ProductUpdate,
)

router = APIRouter(tags=["products"])


def _root_bom(session: Session, root: Component | None, owner: str, mode: ResolveMode) -> BomTree:
    if root is None or root.latest_revision is None:
        raise NotFoundError(f"{owner} has no root assembly yet", owner=owner)
    revision = components.get_revision(session, root.latest_revision.id)
    return bom.resolve_tree(session, revision, mode)


# --- products ----------------------------------------------------------------------


@router.get("/products", response_model=Page[ProductRead])
def list_products(
    page: PageParams = Depends(page_params), session: Session = Depends(get_session)
) -> Page[ProductRead]:
    items, total = service.list_products(session, page)
    return Page(
        items=[ProductRead.model_validate(p) for p in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ProductRead:
    return ProductRead.model_validate(service.create_product(session, actor, payload))


@router.get("/products/{ref}", response_model=ProductRead)
def get_product(ref: str, session: Session = Depends(get_session)) -> ProductRead:
    return ProductRead.model_validate(service.get_product(session, ref))


@router.patch("/products/{ref}", response_model=ProductRead)
def update_product(
    ref: str,
    payload: ProductUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ProductRead:
    product = service.get_product(session, ref)
    return ProductRead.model_validate(service.update_product(session, actor, product, payload))


# --- product models ----------------------------------------------------------------


@router.get("/products/{ref}/models", response_model=list[ProductModelRead])
def list_product_models(
    ref: str, session: Session = Depends(get_session)
) -> list[ProductModelRead]:
    product = service.get_product(session, ref)
    return [ProductModelRead.model_validate(m) for m in service.list_models(session, product)]


@router.post(
    "/products/{ref}/models", response_model=ProductModelRead, status_code=status.HTTP_201_CREATED
)
def create_product_model(
    ref: str,
    payload: ProductModelCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ProductModelRead:
    product = service.get_product(session, ref)
    return ProductModelRead.model_validate(service.create_model(session, actor, product, payload))


@router.get("/models", response_model=list[ProductModelRead])
def list_models(session: Session = Depends(get_session)) -> list[ProductModelRead]:
    return [ProductModelRead.model_validate(m) for m in service.list_models(session)]


@router.get("/models/{ref}", response_model=ProductModelRead)
def get_model(ref: str, session: Session = Depends(get_session)) -> ProductModelRead:
    return ProductModelRead.model_validate(service.get_model(session, ref))


@router.patch("/models/{ref}", response_model=ProductModelRead)
def update_model(
    ref: str,
    payload: ProductModelUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> ProductModelRead:
    model = service.get_model(session, ref)
    return ProductModelRead.model_validate(service.update_model(session, actor, model, payload))


@router.get("/models/{ref}/bom", response_model=BomTree)
def get_model_bom(
    ref: str, mode: ResolveMode = "latest", session: Session = Depends(get_session)
) -> BomTree:
    model = service.get_model(session, ref)
    root = (
        components.get_component_by_id(session, model.root_component_id)
        if model.root_component_id
        else None
    )
    return _root_bom(session, root, model.identifier, mode)


# --- calibers ----------------------------------------------------------------------


@router.get("/calibers", response_model=Page[CaliberRead])
def list_calibers(
    page: PageParams = Depends(page_params), session: Session = Depends(get_session)
) -> Page[CaliberRead]:
    items, total = service.list_calibers(session, page)
    return Page(
        items=[CaliberRead.model_validate(c) for c in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("/calibers", response_model=CaliberRead, status_code=status.HTTP_201_CREATED)
def create_caliber(
    payload: CaliberCreate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> CaliberRead:
    return CaliberRead.model_validate(service.create_caliber(session, actor, payload))


@router.get("/calibers/{ref}", response_model=CaliberRead)
def get_caliber(ref: str, session: Session = Depends(get_session)) -> CaliberRead:
    return CaliberRead.model_validate(service.get_caliber(session, ref))


@router.patch("/calibers/{ref}", response_model=CaliberRead)
def update_caliber(
    ref: str,
    payload: CaliberUpdate,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
) -> CaliberRead:
    caliber = service.get_caliber(session, ref)
    return CaliberRead.model_validate(service.update_caliber(session, actor, caliber, payload))


@router.get("/calibers/{ref}/bom", response_model=BomTree)
def get_caliber_bom(
    ref: str, mode: ResolveMode = "latest", session: Session = Depends(get_session)
) -> BomTree:
    caliber = service.get_caliber(session, ref)
    root = (
        components.get_component_by_id(session, caliber.root_component_id)
        if caliber.root_component_id
        else None
    )
    return _root_bom(session, root, caliber.identifier, mode)
