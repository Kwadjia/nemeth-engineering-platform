"""Component identity and immutable revisions (ADR-004)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.errors import (
    DuplicateIdentifierError,
    ImmutableRevisionError,
    InvalidTransitionError,
)
from nemeth.core.lifecycle import LifecycleState
from nemeth.core.pagination import PageParams
from nemeth.modules.components import service
from nemeth.modules.components.models import ComponentFamily, ComponentKind
from nemeth.modules.components.schemas import (
    ComponentCreate,
    RevisionContent,
    RevisionCreate,
    RevisionUpdate,
)
from tests.factories import add_line, freeze, latest, make_assembly, make_component, release


def test_new_component_starts_at_revision_a_in_concept(session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-001", "Mainplate", material="Brass")
    assert component.revision_count == 1
    rev = component.latest_revision
    assert rev is not None
    assert (rev.revision_number, rev.revision_label) == (1, "A")
    assert rev.lifecycle_state is LifecycleState.CONCEPT
    assert rev.is_frozen is False
    assert rev.material == "Brass"
    assert rev.display_identifier == "T1-MVT-001 Rev A"
    assert component.created_by == "test"


def test_identifier_is_generated_from_product_code_and_family(
    session: Session, actor: Actor
) -> None:
    first = service.create_component(
        session,
        actor,
        ComponentCreate(
            product_code="t9", name="Bezel", kind=ComponentKind.PART, family=ComponentFamily.CASE
        ),
    )
    second = service.create_component(
        session,
        actor,
        ComponentCreate(
            product_code="T9", name="Crown", kind=ComponentKind.PART, family=ComponentFamily.CASE
        ),
    )
    assert (first.identifier, second.identifier) == ("T9-CASE-001", "T9-CASE-002")


def test_duplicate_identifier_is_rejected(session: Session, actor: Actor) -> None:
    make_component(session, actor, "T1-MVT-001")
    with pytest.raises(DuplicateIdentifierError):
        make_component(session, actor, "t1-mvt-001")


def test_editable_revision_accepts_changes(session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-001", material="Brass")
    rev = latest(session, component)
    service.update_revision(
        session, actor, rev, RevisionUpdate(material="CuBe2", finish="Polished")
    )
    assert (rev.material, rev.finish) == ("CuBe2", "Polished")
    assert rev.updated_by == "test"


def test_frozen_revision_rejects_content_changes(session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-001", material="Brass")
    rev = freeze(session, actor, latest(session, component))
    assert rev.is_frozen
    assert rev.frozen_at is not None
    with pytest.raises(ImmutableRevisionError):
        service.update_revision(session, actor, rev, RevisionUpdate(material="Steel"))
    assert rev.material == "Brass"


def test_new_revision_copies_content_and_preserves_history(session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-001", material="Brass")
    rev_a = freeze(session, actor, latest(session, component))
    rev_b = service.create_revision(
        session,
        actor,
        component,
        RevisionCreate(change_summary="Switch to CuBe2", content=RevisionContent(material="CuBe2")),
    )
    assert (rev_b.revision_number, rev_b.revision_label) == (2, "B")
    assert rev_b.lifecycle_state is LifecycleState.CONCEPT
    assert rev_b.material == "CuBe2"
    assert rev_b.change_summary == "Switch to CuBe2"
    # History is intact and linked.
    assert rev_a.material == "Brass"
    assert rev_a.lifecycle_state is LifecycleState.PROTOTYPE
    assert rev_a.superseded_by_id == rev_b.id
    assert component.latest_revision is rev_b or component.latest_revision.id == rev_b.id


def test_revision_letters_continue_past_z(session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-001")
    for _ in range(26):
        service.create_revision(session, actor, component, RevisionCreate(change_summary="iterate"))
    assert component.latest_revision is not None
    assert component.latest_revision.revision_label == "AA"


def test_new_revision_can_branch_from_an_older_revision(session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-001", material="Brass")
    rev_a = latest(session, component)
    rev_b = service.create_revision(
        session,
        actor,
        component,
        RevisionCreate(change_summary="B", content=RevisionContent(material="Steel")),
    )
    rev_c = service.create_revision(
        session,
        actor,
        component,
        RevisionCreate(change_summary="back to A", from_revision_id=rev_a.id),
    )
    assert rev_c.material == "Brass"
    assert rev_c.revision_label == "C"
    assert rev_a.superseded_by_id == rev_b.id  # first successor wins


def test_transition_rules_are_enforced(session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-001")
    rev = latest(session, component)
    with pytest.raises(InvalidTransitionError):
        service.transition_revision(session, actor, rev, LifecycleState.RELEASED)
    release(session, actor, rev)
    assert rev.lifecycle_state is LifecycleState.RELEASED
    assert component.released_revision is not None and component.released_revision.id == rev.id
    with pytest.raises(InvalidTransitionError):
        service.transition_revision(session, actor, rev, LifecycleState.DESIGN)


def test_frozen_revision_rejects_bom_changes(session: Session, actor: Actor) -> None:
    assembly = make_assembly(session, actor, "T1-CASE-001")
    part = make_component(session, actor, "T1-CASE-002", family=ComponentFamily.CASE)
    freeze(session, actor, latest(session, assembly))
    with pytest.raises(ImmutableRevisionError):
        add_line(session, actor, assembly, part)


def test_list_filters_by_latest_revision_state(session: Session, actor: Actor) -> None:
    a = make_component(session, actor, "T1-MVT-001")
    make_component(session, actor, "T1-MVT-002")
    freeze(session, actor, latest(session, a))
    items, total = service.list_components(
        session, page=PageParams(limit=50, offset=0), state=LifecycleState.PROTOTYPE
    )
    assert total == 1 and items[0].identifier == "T1-MVT-001"
    counts = service.count_by_state(session)
    assert counts["PROTOTYPE"] == 1 and counts["CONCEPT"] == 1


# --- through the HTTP API ------------------------------------------------------------


def test_api_create_revise_and_freeze(client: TestClient) -> None:
    created = client.post(
        "/api/v1/components",
        json={
            "identifier": "t1-mvt-001",
            "name": "Mainplate",
            "kind": "PART",
            "family": "MVT",
            "initial_revision": {"material": "Brass", "dimensions": {"diameter_mm": 25.6}},
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["identifier"] == "T1-MVT-001"
    assert body["latest_revision"]["revision_label"] == "A"
    rev_id = body["latest_revision"]["id"]

    for target in ("DESIGN", "PROTOTYPE"):
        moved = client.post(f"/api/v1/revisions/{rev_id}/transition", json={"target_state": target})
        assert moved.status_code == 200, moved.text
    assert moved.json()["is_frozen"] is True

    blocked = client.patch(f"/api/v1/revisions/{rev_id}", json={"material": "Steel"})
    assert blocked.status_code == 409
    assert blocked.headers["content-type"].startswith("application/problem+json")
    assert blocked.json()["type"].endswith("immutable-revision")

    revised = client.post(
        "/api/v1/components/T1-MVT-001/revisions",
        json={"change_summary": "Use steel", "content": {"material": "Steel"}},
    )
    assert revised.status_code == 201, revised.text
    assert revised.json()["revision_label"] == "B"
    assert revised.json()["material"] == "Steel"
    assert revised.json()["dimensions"] == {"diameter_mm": 25.6}

    by_label = client.get("/api/v1/components/T1-MVT-001/revisions/A")
    assert by_label.status_code == 200
    assert by_label.json()["material"] == "Brass"
    assert by_label.json()["superseded_by_id"] == revised.json()["id"]


def test_api_not_found_is_problem_json(client: TestClient) -> None:
    response = client.get("/api/v1/components/NOPE-000")
    assert response.status_code == 404
    assert response.json()["type"].endswith("not-found")
    assert "x-request-id" in response.headers
