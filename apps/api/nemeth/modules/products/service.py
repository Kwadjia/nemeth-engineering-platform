"""Domain rules for products, product models and calibers."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from nemeth.core.audit import stamp_created, stamp_updated
from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError, DuplicateIdentifierError
from nemeth.core.identifiers import normalize_identifier
from nemeth.core.lifecycle import LifecycleState, assert_transition
from nemeth.core.lookup import get_by_ref
from nemeth.core.pagination import PageParams
from nemeth.modules.components import service as components
from nemeth.modules.components.models import Component, ComponentKind
from nemeth.modules.products.models import Caliber, Product, ProductModel
from nemeth.modules.products.schemas import (
    CaliberCreate,
    CaliberUpdate,
    ProductCreate,
    ProductModelCreate,
    ProductModelUpdate,
    ProductUpdate,
)

_PRODUCT_OPTS = (selectinload(Product.models),)
_MODEL_OPTS = (
    selectinload(ProductModel.product),
    selectinload(ProductModel.caliber),
    selectinload(ProductModel.root_component),
)
_CALIBER_OPTS = (selectinload(Caliber.root_component),)


def _assert_unique(
    session: Session, model: type[Product | ProductModel | Caliber], identifier: str
) -> None:
    stmt = select(func.count()).select_from(model).where(model.identifier == identifier)
    if session.execute(stmt).scalar_one():
        raise DuplicateIdentifierError(
            f"{model.__name__} {identifier} already exists", identifier=identifier
        )


def _assert_root_assembly(session: Session, component_id: uuid.UUID | None) -> Component | None:
    if component_id is None:
        return None
    component = components.get_component_by_id(session, component_id)
    if component.kind != ComponentKind.ASSEMBLY:
        raise DomainValidationError(
            f"{component.identifier} is a PART; a root component must be an ASSEMBLY",
            field="root_component_id",
        )
    return component


def _apply_state(entity: Product | ProductModel | Caliber, target: LifecycleState | None) -> None:
    if target is not None and target != entity.lifecycle_state:
        assert_transition(entity.lifecycle_state, target)
        entity.lifecycle_state = target


# --- products ----------------------------------------------------------------------


def list_products(session: Session, page: PageParams) -> tuple[list[Product], int]:
    total = session.execute(select(func.count()).select_from(Product)).scalar_one()
    stmt = (
        select(Product)
        .options(*_PRODUCT_OPTS)
        .order_by(Product.identifier)
        .limit(page.limit)
        .offset(page.offset)
    )
    return list(session.execute(stmt).scalars().unique()), int(total)


def get_product(session: Session, ref: str) -> Product:
    return get_by_ref(session, Product, ref, options=_PRODUCT_OPTS, label="Product")


def create_product(session: Session, actor: Actor, data: ProductCreate) -> Product:
    identifier = normalize_identifier(data.identifier)
    _assert_unique(session, Product, identifier)
    product = Product(
        identifier=identifier,
        name=data.name.strip(),
        description=data.description,
        lifecycle_state=data.lifecycle_state,
        notes=data.notes,
        is_placeholder=data.is_placeholder,
    )
    stamp_created(product, actor)
    session.add(product)
    session.flush()
    return get_product(session, str(product.id))


def update_product(
    session: Session, actor: Actor, product: Product, data: ProductUpdate
) -> Product:
    changes = data.model_dump(exclude_unset=True)
    _apply_state(product, changes.pop("lifecycle_state", None))
    for field, value in changes.items():
        if field == "name" and value is None:
            continue
        setattr(product, field, value.strip() if field == "name" else value)
    stamp_updated(product, actor)
    session.flush()
    return product


# --- product models ----------------------------------------------------------------


def list_models(session: Session, product: Product | None = None) -> list[ProductModel]:
    stmt = select(ProductModel).options(*_MODEL_OPTS).order_by(ProductModel.identifier)
    if product is not None:
        stmt = stmt.where(ProductModel.product_id == product.id)
    return list(session.execute(stmt).scalars().unique())


def get_model(session: Session, ref: str) -> ProductModel:
    return get_by_ref(session, ProductModel, ref, options=_MODEL_OPTS, label="ProductModel")


def create_model(
    session: Session, actor: Actor, product: Product, data: ProductModelCreate
) -> ProductModel:
    identifier = normalize_identifier(data.identifier)
    _assert_unique(session, ProductModel, identifier)
    if data.caliber_id is not None:
        get_by_ref(session, Caliber, str(data.caliber_id), label="Caliber")
    _assert_root_assembly(session, data.root_component_id)
    model = ProductModel(
        product=product,
        identifier=identifier,
        name=data.name.strip(),
        description=data.description,
        lifecycle_state=data.lifecycle_state,
        caliber_id=data.caliber_id,
        root_component_id=data.root_component_id,
        notes=data.notes,
        is_placeholder=data.is_placeholder,
    )
    stamp_created(model, actor)
    session.add(model)
    session.flush()
    return get_model(session, str(model.id))


def update_model(
    session: Session, actor: Actor, model: ProductModel, data: ProductModelUpdate
) -> ProductModel:
    changes = data.model_dump(exclude_unset=True)
    _apply_state(model, changes.pop("lifecycle_state", None))
    if "caliber_id" in changes and changes["caliber_id"] is not None:
        get_by_ref(session, Caliber, str(changes["caliber_id"]), label="Caliber")
    if "root_component_id" in changes:
        _assert_root_assembly(session, changes["root_component_id"])
    for field, value in changes.items():
        if field == "name" and value is None:
            continue
        setattr(model, field, value.strip() if field == "name" else value)
    stamp_updated(model, actor)
    session.flush()
    session.expire(model)
    return get_model(session, str(model.id))


# --- calibers ----------------------------------------------------------------------


def list_calibers(session: Session, page: PageParams) -> tuple[list[Caliber], int]:
    total = session.execute(select(func.count()).select_from(Caliber)).scalar_one()
    stmt = (
        select(Caliber)
        .options(*_CALIBER_OPTS)
        .order_by(Caliber.identifier)
        .limit(page.limit)
        .offset(page.offset)
    )
    return list(session.execute(stmt).scalars().unique()), int(total)


def get_caliber(session: Session, ref: str) -> Caliber:
    return get_by_ref(session, Caliber, ref, options=_CALIBER_OPTS, label="Caliber")


def create_caliber(session: Session, actor: Actor, data: CaliberCreate) -> Caliber:
    identifier = normalize_identifier(data.identifier)
    _assert_unique(session, Caliber, identifier)
    _assert_root_assembly(session, data.root_component_id)
    payload = data.model_dump()
    payload["identifier"] = identifier
    payload["name"] = data.name.strip()
    caliber = Caliber(**payload)
    stamp_created(caliber, actor)
    session.add(caliber)
    session.flush()
    return get_caliber(session, str(caliber.id))


def update_caliber(
    session: Session, actor: Actor, caliber: Caliber, data: CaliberUpdate
) -> Caliber:
    changes = data.model_dump(exclude_unset=True)
    _apply_state(caliber, changes.pop("lifecycle_state", None))
    if "root_component_id" in changes:
        _assert_root_assembly(session, changes["root_component_id"])
    for field, value in changes.items():
        if field == "name" and value is None:
            continue
        setattr(caliber, field, value.strip() if field == "name" else value)
    stamp_updated(caliber, actor)
    session.flush()
    session.expire(caliber)
    return get_caliber(session, str(caliber.id))
