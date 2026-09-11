"""Serialized watches: identifiers, status flow, shared genealogy, dossier."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError
from nemeth.modules.products import service as products
from nemeth.modules.products.schemas import ProductCreate, ProductModelCreate
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.models import BuildAction, PartInstanceStatus
from nemeth.modules.prototypes.schemas import (
    BuildEntryCreate,
    BuildRecordCreate,
    PartInstanceCreate,
    PrototypeCreate,
)
from nemeth.modules.testing import service as testing
from nemeth.modules.testing.schemas import MeasurementCreate, TestRunCreate
from nemeth.modules.watches import service
from nemeth.modules.watches.dossier import build_dossier
from nemeth.modules.watches.models import WatchStatus
from nemeth.modules.watches.schemas import WatchCreate, WatchUpdate
from tests.factories import freeze, latest, make_assembly, make_component


@pytest.fixture
def model(session: Session, actor: Actor) -> products.ProductModel:
    product = products.create_product(
        session, actor, ProductCreate(identifier="T1", name="Test One")
    )
    watch_asm = make_assembly(session, actor, "T1-WATCH-001")
    return products.create_model(
        session,
        actor,
        product,
        ProductModelCreate(identifier="T1.01", name="Ref 01", root_component_id=watch_asm.id),
    )


def _part(session: Session, actor: Actor, identifier: str) -> prototypes.PartInstance:
    component = make_component(session, actor, identifier)
    revision = freeze(session, actor, latest(session, component))
    return prototypes.create_part_instances(
        session, actor, PartInstanceCreate(component_revision_id=revision.id)
    )[0]


def test_identifier_serial_and_status_flow(
    session: Session, actor: Actor, model: products.ProductModel
) -> None:
    first = service.create_watch(session, actor, WatchCreate(product_model_ref="T1.01"))
    second = service.create_watch(
        session,
        actor,
        WatchCreate(product_model_ref=str(model.id), identifier="T1-017", serial_number="017"),
    )
    assert (first.identifier, first.serial_number) == ("T1-001", "001")
    assert (second.identifier, second.serial_number) == ("T1-017", "017")
    assert first.status is WatchStatus.PLANNED

    with pytest.raises(DomainValidationError):
        service.update_watch(session, actor, first, WatchUpdate(status=WatchStatus.DELIVERED))
    service.update_watch(session, actor, first, WatchUpdate(status=WatchStatus.IN_BUILD))
    service.update_watch(session, actor, first, WatchUpdate(status=WatchStatus.BUILT))
    service.update_watch(
        session,
        actor,
        first,
        WatchUpdate(status=WatchStatus.PERSONAL_PROTOTYPE, owner_name="Arthur Nemeth"),
    )
    service.update_watch(session, actor, first, WatchUpdate(status=WatchStatus.IN_SERVICE))
    service.update_watch(session, actor, first, WatchUpdate(status=WatchStatus.PERSONAL_PROTOTYPE))
    assert first.owner_name == "Arthur Nemeth"


def test_parts_move_from_prototype_into_watch_with_history(
    session: Session, actor: Actor, model: products.ProductModel
) -> None:
    prototype = prototypes.create_prototype(
        session, actor, PrototypeCreate(product_code="T1", name="P")
    )
    watch = service.create_watch(
        session, actor, WatchCreate(product_model_ref="T1.01", origin_prototype_ref="T1-P001")
    )
    plate = _part(session, actor, "T1-MVT-002")
    wheel = _part(session, actor, "T1-MVT-011")

    prototypes.create_build_record(
        session,
        actor,
        prototype,
        BuildRecordCreate(
            title="Bench",
            performed_on=date(2026, 9, 1),
            entries=[
                BuildEntryCreate(part_instance_id=plate.id),
                BuildEntryCreate(part_instance_id=wheel.id),
            ],
        ),
    )
    # A part installed in the prototype cannot be cased into the watch until removed.
    with pytest.raises(DomainValidationError):
        prototypes.create_build_record(
            session,
            actor,
            watch,
            BuildRecordCreate(
                title="Case up",
                performed_on=date(2026, 9, 2),
                entries=[BuildEntryCreate(part_instance_id=plate.id)],
            ),
        )
    prototypes.create_build_record(
        session,
        actor,
        prototype,
        BuildRecordCreate(
            title="Strip",
            performed_on=date(2026, 9, 2),
            entries=[BuildEntryCreate(part_instance_id=plate.id, action=BuildAction.REMOVE)],
        ),
    )
    record = prototypes.create_build_record(
        session,
        actor,
        watch,
        BuildRecordCreate(
            title="Case up",
            performed_on=date(2026, 9, 3),
            entries=[BuildEntryCreate(part_instance_id=plate.id, position="movement")],
        ),
    )
    assert record.watch is not None and record.watch.id == watch.id and record.prototype is None
    assert plate.status is PartInstanceStatus.INSTALLED
    assert plate.current_watch_id == watch.id and plate.current_prototype_id is None

    watch = service.get_watch(session, "T1-001")
    assert watch.status is WatchStatus.IN_BUILD  # first build with entries
    config = prototypes.configuration(session, watch)
    assert config.unit_kind == "watch" and config.count == 1
    assert config.rows[0].component.identifier == "T1-MVT-002"
    assert (
        config.rows[0].installed_by is not None and config.rows[0].installed_by.title == "Case up"
    )
    # The wheel is still in the prototype; the plate now answers "which watches contain Rev A".
    assert [
        w.identifier
        for w in prototypes.watches_containing_revision(session, plate.component_revision_id)
    ] == ["T1-001"]
    assert prototypes.configuration(session, prototype).count == 1


def test_dossier_assembles_the_digital_thread(
    session: Session, actor: Actor, model: products.ProductModel
) -> None:
    testing.ensure_builtin_test_types(session, actor)
    watch = service.create_watch(session, actor, WatchCreate(product_model_ref="T1.01"))
    plate = _part(session, actor, "T1-MVT-002")
    prototypes.create_build_record(
        session,
        actor,
        watch,
        BuildRecordCreate(
            title="Case up",
            performed_on=date(2026, 9, 3),
            entries=[BuildEntryCreate(part_instance_id=plate.id)],
        ),
    )
    testing.create_test_run(
        session,
        actor,
        TestRunCreate(
            test_type_code="TIMEGRAPHER",
            watch_ref="T1-001",
            measurements=[
                MeasurementCreate(metric="rate_sec_day", value=Decimal("1.5"), position="DU"),
                MeasurementCreate(metric="rate_sec_day", value=Decimal("-0.5"), position="DD"),
            ],
        ),
    )
    dossier = build_dossier(session, service.get_watch(session, "T1-001"))
    assert dossier.product.identifier == "T1" and dossier.model.identifier == "T1.01"
    assert dossier.configuration.count == 1
    assert [b.title for b in dossier.build_records] == ["Case up"]
    assert len(dossier.test_runs) == 1
    assert dossier.latest_timing is not None and dossier.latest_timing.delta_sec_day == Decimal(
        "2.0"
    )
    assert dossier.watch.build_count == 1 and dossier.watch.installed_count == 1


def test_api_watch_flow(
    client: TestClient, session: Session, actor: Actor, model: products.ProductModel
) -> None:
    created = client.post(
        "/api/v1/watches", json={"product_model_ref": "T1.01", "owner_name": "Arthur Nemeth"}
    )
    assert created.status_code == 201, created.text
    assert created.json()["identifier"] == "T1-001" and created.json()["serial_number"] == "001"

    bad = client.patch("/api/v1/watches/T1-001", json={"status": "RETIRED", "owner_name": None})
    assert bad.status_code == 200  # retiring is always allowed
    again = client.post("/api/v1/watches", json={"product_model_ref": "T1.01"})
    assert again.json()["identifier"] == "T1-002"

    blocked = client.post(
        "/api/v1/watches/T1-001/builds", json={"title": "x", "performed_on": "2026-09-11"}
    )
    assert blocked.status_code == 422  # retired

    dossier = client.get("/api/v1/watches/T1-002/dossier")
    assert dossier.status_code == 200, dossier.text
    assert dossier.json()["configuration"]["unit_kind"] == "watch"
    assert dossier.json()["build_records"] == []

    listed = client.get("/api/v1/models/T1.01/watches").json()
    assert [w["identifier"] for w in listed] == ["T1-001", "T1-002"]
    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["watch_count"] == 2
