"""Products, models, calibers, the N1 seed and the dashboard summary."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError, InvalidTransitionError
from nemeth.core.lifecycle import LifecycleState
from nemeth.core.pagination import PageParams
from nemeth.modules.products import service
from nemeth.modules.products.schemas import (
    CaliberCreate,
    CaliberUpdate,
    ProductCreate,
    ProductModelCreate,
    ProductUpdate,
)
from nemeth.seed.n1 import seed_n1
from tests.factories import make_assembly, make_component


def test_product_model_and_caliber_link_together(session: Session, actor: Actor) -> None:
    product = service.create_product(
        session, actor, ProductCreate(identifier="t1", name="Test One")
    )
    assert product.identifier == "T1"
    movement = make_assembly(session, actor, "T1-MVT-001")
    watch = make_assembly(session, actor, "T1-WATCH-001")
    caliber = service.create_caliber(
        session,
        actor,
        CaliberCreate(
            identifier="CAL-T1",
            name="Caliber T1",
            root_component_id=movement.id,
            frequency_bph=21600,
        ),
    )
    model = service.create_model(
        session,
        actor,
        product,
        ProductModelCreate(
            identifier="T1.01", name="T1 Ref 01", caliber_id=caliber.id, root_component_id=watch.id
        ),
    )
    assert model.caliber is not None and model.caliber.identifier == "CAL-T1"
    assert model.root_component is not None and model.root_component.identifier == "T1-WATCH-001"
    assert service.get_product(session, "T1").models[0].identifier == "T1.01"


def test_root_component_must_be_an_assembly(session: Session, actor: Actor) -> None:
    part = make_component(session, actor, "T1-MVT-002")
    with pytest.raises(DomainValidationError):
        service.create_caliber(
            session, actor, CaliberCreate(identifier="CAL-T1", name="x", root_component_id=part.id)
        )


def test_lifecycle_changes_are_validated_on_update(session: Session, actor: Actor) -> None:
    product = service.create_product(session, actor, ProductCreate(identifier="T1", name="Test"))
    with pytest.raises(InvalidTransitionError):
        service.update_product(
            session, actor, product, ProductUpdate(lifecycle_state=LifecycleState.RELEASED)
        )
    service.update_product(
        session, actor, product, ProductUpdate(lifecycle_state=LifecycleState.DESIGN)
    )
    assert product.lifecycle_state is LifecycleState.DESIGN


def test_caliber_specification_json_is_kept(session: Session, actor: Actor) -> None:
    caliber = service.create_caliber(
        session,
        actor,
        CaliberCreate(
            identifier="CAL-T1", name="x", specification={"tooth_counts": {"center": 80}}
        ),
    )
    updated = service.update_caliber(session, actor, caliber, CaliberUpdate(jewel_count=17))
    assert updated.jewel_count == 17
    assert updated.specification == {"tooth_counts": {"center": 80}}


def test_seed_is_idempotent_and_wires_the_n1_tree(session: Session) -> None:
    first = seed_n1(session)
    second = seed_n1(session)
    assert first.created and not second.created
    assert first.components == 29
    assert first.bom_lines == 28

    model = service.get_model(session, "N1.01")
    assert model.is_placeholder
    assert model.caliber is not None and model.caliber.identifier == "CAL-N1"
    assert model.root_component is not None and model.root_component.identifier == "N1-WATCH-001"

    items, total = service.list_calibers(session, PageParams(limit=10, offset=0))
    assert total == 1 and items[0].root_component is not None
    assert items[0].root_component.identifier == "N1-MVT-001"


def test_api_seeded_bom_and_dashboard(client: TestClient, session: Session) -> None:
    seed_n1(session)
    tree = client.get("/api/v1/models/N1.01/bom").json()
    assert tree["root_component"]["identifier"] == "N1-WATCH-001"
    assert tree["line_count"] == 28
    assert tree["max_depth"] == 3  # watch -> movement -> barrel assembly -> barrel

    caliber_tree = client.get("/api/v1/calibers/CAL-N1/bom?mode=released").json()
    assert caliber_tree["unresolved_count"] == caliber_tree["line_count"]  # nothing is released yet

    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["component_count"] == 29
    assert summary["assembly_count"] == 10
    assert summary["components_by_state"]["CONCEPT"] == 29
    assert summary["products"][0]["identifier"] == "N1"
    assert len(summary["recent_revisions"]) == 8

    health = client.get("/api/v1/health").json()
    assert health["status"] == "ok" and health["database"] == "ok"
