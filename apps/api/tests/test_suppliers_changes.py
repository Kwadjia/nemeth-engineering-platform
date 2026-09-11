"""Suppliers and engineering changes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError, NotFoundError
from nemeth.core.pagination import PageParams
from nemeth.modules.changes import service as changes
from nemeth.modules.changes.models import ChangeRole, ChangeStatus
from nemeth.modules.changes.schemas import ChangeCreate, ChangeUpdate
from nemeth.modules.components import service as components
from nemeth.modules.components.schemas import RevisionCreate, RevisionUpdate
from nemeth.modules.experiments import service as experiments
from nemeth.modules.experiments.schemas import ExperimentCreate
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.schemas import PartInstanceCreate
from nemeth.modules.suppliers import service as suppliers
from nemeth.modules.suppliers.models import SupplierKind
from nemeth.modules.suppliers.schemas import SupplierCreate, SupplierUpdate
from tests.factories import freeze, latest, make_component


def test_supplier_register_and_links(session: Session, actor: Actor) -> None:
    shop = suppliers.create_supplier(
        session,
        actor,
        SupplierCreate(
            name="Detroit Precision",
            kind=SupplierKind.MACHINE_SHOP,
            capabilities="5-axis, wire EDM",
        ),
    )
    plating = suppliers.create_supplier(
        session, actor, SupplierCreate(name="Plate Co", kind=SupplierKind.PLATING)
    )
    assert (shop.identifier, plating.identifier) == ("SUP-001", "SUP-002")

    component = make_component(session, actor, "T1-MVT-011", "Escape Wheel")
    revision = latest(session, component)
    components.update_revision(session, actor, revision, RevisionUpdate(supplier_id=shop.id))
    assert revision.supplier_id == shop.id
    with pytest.raises(NotFoundError):
        components.update_revision(
            session, actor, revision, RevisionUpdate(supplier_id=component.id)
        )

    freeze(session, actor, revision)
    part = prototypes.create_part_instances(
        session,
        actor,
        PartInstanceCreate(component_revision_id=revision.id, supplier_id=plating.id),
    )[0]
    assert part.supplier is not None and part.supplier.identifier == "SUP-002"

    assert [r.id for r in suppliers.revisions_for(session, shop)] == [revision.id]
    assert [p.id for p in suppliers.part_instances_for(session, plating)] == [part.id]
    items, total = suppliers.list_suppliers(session, PageParams(limit=10, offset=0), q="edm")
    assert total == 1 and items[0].identifier == "SUP-001"
    suppliers.update_supplier(session, actor, plating, SupplierUpdate(is_active=False))
    active, _ = suppliers.list_suppliers(
        session, PageParams(limit=10, offset=0), include_inactive=False
    )
    assert [s.identifier for s in active] == ["SUP-001"]


def test_change_flow_with_evidence(session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-004", "Barrel")
    rev_a = freeze(session, actor, latest(session, component))
    rev_b = components.create_revision(
        session, actor, component, RevisionCreate(change_summary="More endshake")
    )
    experiment = experiments.create_experiment(session, actor, ExperimentCreate(title="Endshake"))

    change = changes.create_change(
        session,
        actor,
        ChangeCreate(
            title="Increase barrel arbor endshake",
            reason="Low amplitude in P001",
            affected_revision_ids=[rev_a.id],
            experiment_refs=["EXP-001"],
        ),
    )
    assert change.identifier == "ECR-0001" and change.status is ChangeStatus.DRAFT
    assert change.requested_by == "Test User"
    assert [(x.role, x.component_revision_id) for x in change.revision_links] == [
        (ChangeRole.AFFECTED, rev_a.id)
    ]
    assert [x.experiment_id for x in change.experiment_links] == [experiment.id]

    # Cannot implement without a proposed revision, nor skip states.
    changes.update_change(session, actor, change, ChangeUpdate(status=ChangeStatus.PROPOSED))
    with pytest.raises(DomainValidationError):
        changes.update_change(session, actor, change, ChangeUpdate(status=ChangeStatus.IMPLEMENTED))
    changes.update_change(session, actor, change, ChangeUpdate(status=ChangeStatus.APPROVED))
    assert change.approved_on is not None and change.approved_by == "Test User"
    with pytest.raises(DomainValidationError):
        changes.update_change(session, actor, change, ChangeUpdate(status=ChangeStatus.IMPLEMENTED))
    changes.link_revision(session, actor, change, rev_b.id, ChangeRole.PROPOSED)
    changes.update_change(session, actor, change, ChangeUpdate(status=ChangeStatus.IMPLEMENTED))
    assert change.status is ChangeStatus.IMPLEMENTED and change.implemented_on is not None

    # Closed: links are frozen; both revisions know their change.
    with pytest.raises(DomainValidationError):
        changes.link_experiment(session, actor, change, "EXP-001")
    assert [c.identifier for c in changes.for_revision(session, rev_a.id)] == ["ECR-0001"]
    assert [c.identifier for c in changes.for_revision(session, rev_b.id)] == ["ECR-0001"]
    assert changes.open_count(session) == 0


def test_rejection_and_send_back(session: Session, actor: Actor) -> None:
    change = changes.create_change(session, actor, ChangeCreate(title="Try titanium"))
    changes.update_change(session, actor, change, ChangeUpdate(status=ChangeStatus.PROPOSED))
    changes.update_change(session, actor, change, ChangeUpdate(status=ChangeStatus.DRAFT))
    changes.update_change(session, actor, change, ChangeUpdate(status=ChangeStatus.REJECTED))
    with pytest.raises(DomainValidationError):
        changes.update_change(session, actor, change, ChangeUpdate(status=ChangeStatus.DRAFT))


def test_api_suppliers_and_changes(client: TestClient, session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-004")
    revision = latest(session, component)
    created = client.post(
        "/api/v1/suppliers", json={"name": "Detroit Precision", "kind": "MACHINE_SHOP"}
    )
    assert created.status_code == 201 and created.json()["identifier"] == "SUP-001"

    change = client.post(
        "/api/v1/changes",
        json={"title": "Clearance", "reason": "Rub", "affected_revision_ids": [str(revision.id)]},
    )
    assert change.status_code == 201, change.text
    body = change.json()
    assert (
        body["identifier"] == "ECR-0001"
        and body["revisions"][0]["component"]["identifier"] == "T1-MVT-004"
    )

    bad = client.patch("/api/v1/changes/ECR-0001", json={"status": "APPROVED"})
    assert bad.status_code == 422

    listed = client.get(f"/api/v1/revisions/{revision.id}/changes").json()
    assert listed[0]["identifier"] == "ECR-0001"
    summary = client.get("/api/v1/dashboard/summary").json()
    assert (
        summary["open_change_count"] == 1 and summary["open_changes"][0]["identifier"] == "ECR-0001"
    )
    assert summary["supplier_count"] == 1

    assert (
        client.delete(f"/api/v1/changes/ECR-0001/revisions/{revision.id}?role=AFFECTED").status_code
        == 204
    )
    assert client.get("/api/v1/changes/ECR-0001").json()["revisions"] == []
