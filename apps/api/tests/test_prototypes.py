"""Prototypes, part instances, build records and derived configuration (ADR-008)."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError
from nemeth.core.pagination import PageParams
from nemeth.modules.prototypes import service
from nemeth.modules.prototypes.models import (
    BuildAction,
    PartInstanceStatus,
    PartSource,
    PrototypeStatus,
)
from nemeth.modules.prototypes.schemas import (
    BuildEntryCreate,
    BuildRecordCreate,
    PartInstanceCreate,
    PrototypeCreate,
    PrototypeUpdate,
)
from nemeth.seed.n1 import seed_n1
from tests.factories import freeze, latest, make_component


def _prototype(session: Session, actor: Actor, code: str = "T1") -> service.Prototype:
    return service.create_prototype(
        session, actor, PrototypeCreate(product_code=code, name=f"{code} first build")
    )


def _instances(
    session: Session, actor: Actor, identifier: str, quantity: int = 1
) -> list[service.PartInstance]:
    component = make_component(session, actor, identifier, material="Brass")
    revision = freeze(session, actor, latest(session, component))
    return service.create_part_instances(
        session,
        actor,
        PartInstanceCreate(
            component_revision_id=revision.id, quantity=quantity, source=PartSource.IN_HOUSE
        ),
    )


def test_prototype_identifier_is_generated_per_product(session: Session, actor: Actor) -> None:
    first = _prototype(session, actor)
    second = _prototype(session, actor)
    assert (first.identifier, second.identifier) == ("T1-P001", "T1-P002")
    assert first.status is PrototypeStatus.PLANNED
    assert first.installed_count == 0


def test_prototype_status_cannot_move_backwards(session: Session, actor: Actor) -> None:
    prototype = _prototype(session, actor)
    service.update_prototype(
        session, actor, prototype, PrototypeUpdate(status=PrototypeStatus.ACTIVE)
    )
    with pytest.raises(DomainValidationError):
        service.update_prototype(
            session, actor, prototype, PrototypeUpdate(status=PrototypeStatus.PLANNED)
        )


def test_part_instances_require_a_frozen_revision(session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-002")
    revision = latest(session, component)
    with pytest.raises(DomainValidationError) as excinfo:
        service.create_part_instances(
            session, actor, PartInstanceCreate(component_revision_id=revision.id)
        )
    assert "frozen" in str(excinfo.value)


def test_part_instances_are_numbered_and_linked_to_exact_revision(
    session: Session, actor: Actor
) -> None:
    instances = _instances(session, actor, "T1-MVT-011", quantity=3)
    assert [i.identifier for i in instances] == ["PI-00001", "PI-00002", "PI-00003"]
    assert all(i.status is PartInstanceStatus.AVAILABLE for i in instances)
    assert instances[0].revision.revision_label == "A"
    assert instances[0].component.identifier == "T1-MVT-011"


def test_build_record_installs_parts_and_configuration_is_derived(
    session: Session, actor: Actor
) -> None:
    prototype = _prototype(session, actor)
    plate = _instances(session, actor, "T1-MVT-002")[0]
    wheel = _instances(session, actor, "T1-MVT-011")[0]
    record = service.create_build_record(
        session,
        actor,
        prototype,
        BuildRecordCreate(
            title="Movement build",
            performed_on=date(2026, 9, 11),
            procedure="Fit mainplate, then escape wheel. Moebius 9010 on pivots.",
            entries=[
                BuildEntryCreate(part_instance_id=plate.id, position="main"),
                BuildEntryCreate(part_instance_identifier="pi-00002", position="train"),
            ],
        ),
    )
    assert record.identifier == "BR-00001"
    assert record.performed_by == "Test User"
    assert [e.sequence for e in record.entries] == [1, 2]
    assert plate.status is PartInstanceStatus.INSTALLED
    assert wheel.current_prototype_id == prototype.id

    config = service.configuration(session, service.get_prototype(session, prototype.identifier))
    assert config.count == 2
    assert [(r.component.identifier, r.revision.revision_label) for r in config.rows] == [
        ("T1-MVT-002", "A"),
        ("T1-MVT-011", "A"),
    ]
    assert config.rows[0].position == "main"
    assert (
        config.rows[0].installed_by is not None
        and config.rows[0].installed_by.identifier == "BR-00001"
    )
    # First build moves a planned prototype to BUILDING.
    assert service.get_prototype(session, prototype.identifier).status is PrototypeStatus.BUILDING


def test_removal_and_reinstall_preserve_history(session: Session, actor: Actor) -> None:
    prototype = _prototype(session, actor)
    other = _prototype(session, actor)
    wheel = _instances(session, actor, "T1-MVT-011")[0]

    install = BuildRecordCreate(
        title="Install",
        performed_on=date(2026, 9, 1),
        entries=[BuildEntryCreate(part_instance_id=wheel.id)],
    )
    service.create_build_record(session, actor, prototype, install)

    # Cannot install the same physical part somewhere else while it is installed.
    with pytest.raises(DomainValidationError):
        service.create_build_record(session, actor, other, install)
    # Cannot remove from a unit it is not in.
    with pytest.raises(DomainValidationError):
        service.create_build_record(
            session,
            actor,
            other,
            BuildRecordCreate(
                title="Remove",
                performed_on=date(2026, 9, 2),
                entries=[BuildEntryCreate(part_instance_id=wheel.id, action=BuildAction.REMOVE)],
            ),
        )

    service.create_build_record(
        session,
        actor,
        prototype,
        BuildRecordCreate(
            title="Swap out",
            performed_on=date(2026, 9, 3),
            entries=[BuildEntryCreate(part_instance_id=wheel.id, action=BuildAction.REMOVE)],
        ),
    )
    assert wheel.status is PartInstanceStatus.REMOVED and wheel.current_prototype_id is None
    assert service.configuration(session, prototype).count == 0

    service.create_build_record(
        session,
        actor,
        other,
        BuildRecordCreate(title="Salvage", performed_on=date(2026, 9, 4), entries=install.entries),
    )
    assert wheel.current_prototype_id == other.id
    history = service.list_build_records(session, prototype)
    assert [b.title for b in history] == ["Swap out", "Install"]
    assert [
        p.identifier
        for p in service.prototypes_containing_revision(session, wheel.component_revision_id)
    ] == [other.identifier]


def test_same_part_twice_in_one_record_is_rejected(session: Session, actor: Actor) -> None:
    prototype = _prototype(session, actor)
    wheel = _instances(session, actor, "T1-MVT-011")[0]
    with pytest.raises(DomainValidationError):
        service.create_build_record(
            session,
            actor,
            prototype,
            BuildRecordCreate(
                title="x",
                performed_on=date(2026, 9, 1),
                entries=[
                    BuildEntryCreate(part_instance_id=wheel.id),
                    BuildEntryCreate(part_instance_id=wheel.id, action=BuildAction.REMOVE),
                ],
            ),
        )


def test_retired_prototype_accepts_no_builds(session: Session, actor: Actor) -> None:
    prototype = _prototype(session, actor)
    service.update_prototype(
        session, actor, prototype, PrototypeUpdate(status=PrototypeStatus.RETIRED)
    )
    with pytest.raises(DomainValidationError):
        service.create_build_record(
            session, actor, prototype, BuildRecordCreate(title="x", performed_on=date(2026, 9, 1))
        )


def test_seed_creates_planned_n1_p001(session: Session) -> None:
    seed_n1(session)
    prototype = service.get_prototype(session, "N1-P001")
    assert prototype.status is PrototypeStatus.PLANNED
    assert prototype.is_placeholder
    assert prototype.product_model is not None and prototype.product_model.identifier == "N1.01"
    items, total = service.list_part_instances(session, PageParams(limit=10, offset=0))
    assert total == 0 and items == []


def test_api_prototype_flow(client: TestClient, session: Session, actor: Actor) -> None:
    wheel = _instances(session, actor, "T1-MVT-011")[0]
    created = client.post("/api/v1/prototypes", json={"product_code": "t1", "name": "Bench build"})
    assert created.status_code == 201, created.text
    assert created.json()["identifier"] == "T1-P001"

    blocked = client.post(
        "/api/v1/part-instances",
        json={"component_revision_id": str(wheel.component_revision_id), "quantity": 0},
    )
    assert blocked.status_code == 422

    build = client.post(
        "/api/v1/prototypes/T1-P001/builds",
        json={
            "title": "Fit wheel",
            "performed_on": "2026-09-11",
            "entries": [{"part_instance_identifier": "PI-00001", "position": "train"}],
        },
    )
    assert build.status_code == 201, build.text
    assert build.json()["entries"][0]["component"]["identifier"] == "T1-MVT-011"

    config = client.get("/api/v1/prototypes/T1-P001/configuration").json()
    assert config["count"] == 1 and config["rows"][0]["revision"]["revision_label"] == "A"

    listed = client.get("/api/v1/components/T1-MVT-011/part-instances").json()
    assert listed[0]["current_prototype"]["identifier"] == "T1-P001"

    contains = client.get(f"/api/v1/revisions/{wheel.component_revision_id}/prototypes").json()
    assert [p["identifier"] for p in contains] == ["T1-P001"]

    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["active_prototype"]["identifier"] == "T1-P001"
    assert summary["prototype_count"] == 1
