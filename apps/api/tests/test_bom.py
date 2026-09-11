"""Recursive BOM structure, resolution modes, cycle prevention and where-used (ADR-006)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.errors import BomCycleError, DomainValidationError, ImmutableRevisionError
from nemeth.core.lifecycle import LifecycleState
from nemeth.modules.bom import service as bom
from nemeth.modules.bom.schemas import BomLineUpdate
from nemeth.modules.components import service as components
from nemeth.modules.components.models import ComponentFamily
from nemeth.modules.components.schemas import RevisionCreate
from tests.factories import add_line, freeze, latest, make_assembly, make_component, release


@pytest.fixture
def movement(session: Session, actor: Actor) -> dict[str, object]:
    """Movement → Gear Train → (Center, Escape); Movement → Mainplate."""
    mvt = make_assembly(session, actor, "T1-MVT-001", "Movement")
    train = make_assembly(session, actor, "T1-MVT-007", "Gear Train")
    plate = make_component(session, actor, "T1-MVT-002", "Mainplate")
    center = make_component(session, actor, "T1-MVT-008", "Center Wheel")
    escape = make_component(session, actor, "T1-MVT-011", "Escape Wheel")
    add_line(session, actor, mvt, plate)
    add_line(session, actor, mvt, train)
    add_line(session, actor, train, center)
    add_line(session, actor, train, escape, quantity=1)
    return {"mvt": mvt, "train": train, "plate": plate, "center": center, "escape": escape}


def test_tree_is_recursive_and_ordered_by_find_number(
    session: Session, movement: dict[str, object]
) -> None:
    tree = bom.resolve_tree(session, latest(session, movement["mvt"]), "latest")  # type: ignore[arg-type]
    assert [n.line.child_component.identifier for n in tree.nodes] == ["T1-MVT-002", "T1-MVT-007"]
    assert [n.line.find_number for n in tree.nodes] == [10, 20]
    train_node = tree.nodes[1]
    assert [n.line.child_component.identifier for n in train_node.children] == [
        "T1-MVT-008",
        "T1-MVT-011",
    ]
    assert train_node.children[0].level == 2
    assert tree.line_count == 4
    assert tree.max_depth == 2
    assert tree.unresolved_count == 0


def test_flat_view_carries_level_path_and_extended_quantity(session: Session, actor: Actor) -> None:
    watch = make_assembly(session, actor, "T1-WATCH-001")
    dial = make_assembly(session, actor, "T1-DIAL-001")
    marker = make_component(session, actor, "T1-DIAL-003", family=ComponentFamily.DIAL)
    add_line(session, actor, watch, dial, quantity=2)  # two dials, absurd but arithmetic-friendly
    add_line(session, actor, dial, marker, quantity=12)
    flat = bom.flatten_tree(bom.resolve_tree(session, latest(session, watch), "latest"))
    rows = {r.component.identifier: r for r in flat.rows}
    assert rows["T1-DIAL-001"].level == 1
    assert rows["T1-DIAL-003"].level == 2
    assert rows["T1-DIAL-003"].path == ["T1-WATCH-001", "T1-DIAL-001", "T1-DIAL-003"]
    assert rows["T1-DIAL-003"].extended_quantity == Decimal(24)


def test_unpinned_lines_follow_latest_revision(
    session: Session, actor: Actor, movement: dict[str, object]
) -> None:
    escape = movement["escape"]
    components.create_revision(session, actor, escape, RevisionCreate(change_summary="B"))  # type: ignore[arg-type]
    tree = bom.resolve_tree(session, latest(session, movement["mvt"]), "latest")  # type: ignore[arg-type]
    escape_node = tree.nodes[1].children[1]
    assert escape_node.resolution == "latest"
    assert escape_node.resolved_revision is not None
    assert escape_node.resolved_revision.revision_label == "B"


def test_pinned_line_stays_on_its_revision(session: Session, actor: Actor) -> None:
    train = make_assembly(session, actor, "T1-MVT-007")
    escape = make_component(session, actor, "T1-MVT-011")
    rev_a = latest(session, escape)
    add_line(session, actor, train, escape, pin=rev_a)
    components.create_revision(session, actor, escape, RevisionCreate(change_summary="B"))
    tree = bom.resolve_tree(session, latest(session, train), "latest")
    node = tree.nodes[0]
    assert node.resolution == "pinned"
    assert node.line.is_pinned
    assert node.resolved_revision is not None and node.resolved_revision.revision_label == "A"


def test_released_mode_reports_unresolved_children(session: Session, actor: Actor) -> None:
    train = make_assembly(session, actor, "T1-MVT-007")
    center = make_component(session, actor, "T1-MVT-008")
    escape = make_component(session, actor, "T1-MVT-011")
    add_line(session, actor, train, center)
    add_line(session, actor, train, escape)
    release(session, actor, latest(session, center))
    tree = bom.resolve_tree(session, latest(session, train), "released")
    by_id = {n.line.child_component.identifier: n for n in tree.nodes}
    assert by_id["T1-MVT-008"].resolution == "released"
    assert by_id["T1-MVT-011"].resolution == "unresolved"
    assert by_id["T1-MVT-011"].resolved_revision is None
    assert tree.unresolved_count == 1


def test_obsolete_revisions_are_skipped_in_latest_mode(session: Session, actor: Actor) -> None:
    train = make_assembly(session, actor, "T1-MVT-007")
    escape = make_component(session, actor, "T1-MVT-011")
    add_line(session, actor, train, escape)
    rev_b = components.create_revision(session, actor, escape, RevisionCreate(change_summary="B"))
    components.transition_revision(session, actor, rev_b, LifecycleState.OBSOLETE)
    tree = bom.resolve_tree(session, latest(session, train), "latest")
    assert tree.nodes[0].resolved_revision is not None
    assert tree.nodes[0].resolved_revision.revision_label == "A"


def test_parts_cannot_have_bom_lines(session: Session, actor: Actor) -> None:
    part = make_component(session, actor, "T1-MVT-002")
    other = make_component(session, actor, "T1-MVT-003")
    with pytest.raises(DomainValidationError):
        add_line(session, actor, part, other)


def test_direct_and_indirect_cycles_are_rejected(
    session: Session, actor: Actor, movement: dict[str, object]
) -> None:
    mvt, train = movement["mvt"], movement["train"]
    with pytest.raises(BomCycleError):
        add_line(session, actor, mvt, mvt)  # type: ignore[arg-type]
    with pytest.raises(BomCycleError):
        add_line(session, actor, train, mvt)  # type: ignore[arg-type]  # train is inside mvt


def test_cycle_check_sees_through_every_revision(session: Session, actor: Actor) -> None:
    outer = make_assembly(session, actor, "T1-CASE-001")
    inner = make_assembly(session, actor, "T1-CASE-002")
    add_line(session, actor, outer, inner)
    # A new revision of `inner` still cannot swallow `outer`.
    components.create_revision(session, actor, inner, RevisionCreate(change_summary="B"))
    with pytest.raises(BomCycleError):
        add_line(session, actor, inner, outer)


def test_pin_must_belong_to_child(session: Session, actor: Actor) -> None:
    train = make_assembly(session, actor, "T1-MVT-007")
    escape = make_component(session, actor, "T1-MVT-011")
    center = make_component(session, actor, "T1-MVT-008")
    with pytest.raises(DomainValidationError):
        add_line(session, actor, train, escape, pin=latest(session, center))


def test_find_numbers_are_unique_and_auto_assigned(session: Session, actor: Actor) -> None:
    train = make_assembly(session, actor, "T1-MVT-007")
    a = make_component(session, actor, "T1-MVT-008")
    b = make_component(session, actor, "T1-MVT-009")
    first = add_line(session, actor, train, a)
    second = add_line(session, actor, train, b)
    assert (first.find_number, second.find_number) == (10, 20)
    with pytest.raises(DomainValidationError):
        bom.update_line(session, actor, second, BomLineUpdate(find_number=10))


def test_new_revision_copies_bom_lines(
    session: Session, actor: Actor, movement: dict[str, object]
) -> None:
    mvt = movement["mvt"]
    rev_a = freeze(session, actor, latest(session, mvt))  # type: ignore[arg-type]
    rev_b = components.create_revision(session, actor, mvt, RevisionCreate(change_summary="B"))  # type: ignore[arg-type]
    rev_b = components.get_revision(session, rev_b.id)
    assert [line.child_component_id for line in rev_b.bom_lines] == [
        line.child_component_id for line in rev_a.bom_lines
    ]
    # And the copy is independent: editing B does not touch A.
    bom.remove_line(session, actor, rev_b.bom_lines[0])
    assert len(components.get_revision(session, rev_a.id).bom_lines) == 2
    assert len(components.get_revision(session, rev_b.id).bom_lines) == 1


def test_frozen_parent_blocks_line_edits_and_removal(session: Session, actor: Actor) -> None:
    train = make_assembly(session, actor, "T1-MVT-007")
    escape = make_component(session, actor, "T1-MVT-011")
    line = add_line(session, actor, train, escape)
    freeze(session, actor, latest(session, train))
    with pytest.raises(ImmutableRevisionError):
        bom.update_line(session, actor, line, BomLineUpdate(quantity=Decimal(2)))
    with pytest.raises(ImmutableRevisionError):
        bom.remove_line(session, actor, line)


def test_where_used_lists_every_parent_revision(
    session: Session, actor: Actor, movement: dict[str, object]
) -> None:
    escape, train = movement["escape"], movement["train"]
    components.create_revision(session, actor, train, RevisionCreate(change_summary="B"))  # type: ignore[arg-type]
    rows = bom.where_used(session, escape)  # type: ignore[arg-type]
    assert [(r.parent_component.identifier, r.parent_revision.revision_label) for r in rows] == [
        ("T1-MVT-007", "B"),
        ("T1-MVT-007", "A"),
    ]


# --- through the HTTP API ------------------------------------------------------------


def test_api_bom_endpoints(client: TestClient) -> None:
    def create(identifier: str, kind: str) -> dict[str, object]:
        r = client.post(
            "/api/v1/components",
            json={"identifier": identifier, "name": identifier, "kind": kind, "family": "MVT"},
        )
        assert r.status_code == 201, r.text
        return r.json()  # type: ignore[no-any-return]

    mvt = create("T1-MVT-001", "ASSEMBLY")
    train = create("T1-MVT-007", "ASSEMBLY")
    wheel = create("T1-MVT-008", "PART")
    mvt_rev = mvt["latest_revision"]["id"]  # type: ignore[index]
    train_rev = train["latest_revision"]["id"]  # type: ignore[index]

    r = client.post(
        f"/api/v1/revisions/{mvt_rev}/bom-lines", json={"child_component_identifier": "t1-mvt-007"}
    )
    assert r.status_code == 201, r.text
    r = client.post(
        f"/api/v1/revisions/{train_rev}/bom-lines",
        json={"child_component_id": wheel["id"], "quantity": "2"},
    )
    assert r.status_code == 201, r.text
    line_id = r.json()["id"]

    cycle = client.post(
        f"/api/v1/revisions/{train_rev}/bom-lines",
        json={"child_component_identifier": "T1-MVT-001"},
    )
    assert cycle.status_code == 409 and cycle.json()["type"].endswith("bom-cycle")

    tree = client.get("/api/v1/components/T1-MVT-001/bom").json()
    assert tree["line_count"] == 2
    assert tree["nodes"][0]["children"][0]["line"]["child_component"]["identifier"] == "T1-MVT-008"

    flat = client.get(f"/api/v1/revisions/{mvt_rev}/bom/flat").json()
    assert [row["level"] for row in flat["rows"]] == [1, 2]
    assert Decimal(flat["rows"][1]["extended_quantity"]) == Decimal(2)

    used = client.get("/api/v1/components/T1-MVT-008/where-used").json()
    assert used[0]["parent_component"]["identifier"] == "T1-MVT-007"

    assert client.patch(f"/api/v1/bom-lines/{line_id}", json={"quantity": "3"}).status_code == 200
    assert client.delete(f"/api/v1/bom-lines/{line_id}").status_code == 204
    assert client.get(f"/api/v1/bom-lines/{line_id}").status_code == 404
