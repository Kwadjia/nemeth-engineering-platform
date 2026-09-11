"""Experiments: identifiers, status flow, links, seed."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.errors import DomainValidationError
from nemeth.core.pagination import PageParams
from nemeth.modules.experiments import service
from nemeth.modules.experiments.models import ExperimentOutcome, ExperimentStatus
from nemeth.modules.experiments.schemas import (
    ExperimentCreate,
    ExperimentUpdate,
    LinkPrototype,
    LinkRevision,
)
from nemeth.modules.prototypes import service as prototypes
from nemeth.modules.prototypes.schemas import PrototypeCreate
from nemeth.seed.n1 import seed_n1
from tests.factories import latest, make_component


def test_identifiers_and_status_flow(session: Session, actor: Actor) -> None:
    first = service.create_experiment(
        session,
        actor,
        ExperimentCreate(title="Endshake vs amplitude", hypothesis="More endshake, more amplitude"),
    )
    second = service.create_experiment(session, actor, ExperimentCreate(title="Second"))
    assert (first.identifier, second.identifier) == ("EXP-001", "EXP-002")
    assert first.status is ExperimentStatus.PLANNED

    with pytest.raises(DomainValidationError):
        service.update_experiment(
            session, actor, first, ExperimentUpdate(status=ExperimentStatus.COMPLETED)
        )
    service.update_experiment(
        session, actor, first, ExperimentUpdate(status=ExperimentStatus.IN_PROGRESS)
    )
    service.update_experiment(
        session,
        actor,
        first,
        ExperimentUpdate(
            status=ExperimentStatus.COMPLETED,
            outcome=ExperimentOutcome.IMPROVEMENT,
            results="251° → 276°",
        ),
    )
    assert (
        first.status is ExperimentStatus.COMPLETED
        and first.outcome is ExperimentOutcome.IMPROVEMENT
    )
    with pytest.raises(DomainValidationError):
        service.update_experiment(
            session, actor, first, ExperimentUpdate(status=ExperimentStatus.IN_PROGRESS)
        )


def test_links_to_prototypes_and_revisions(session: Session, actor: Actor) -> None:
    prototype = prototypes.create_prototype(
        session, actor, PrototypeCreate(product_code="T1", name="P")
    )
    component = make_component(session, actor, "T1-MVT-006", "Barrel Arbor")
    revision = latest(session, component)
    experiment = service.create_experiment(
        session, actor, ExperimentCreate(title="Arbor endshake", prototype_ids=[prototype.id])
    )
    assert [link.prototype.identifier for link in experiment.prototype_links] == ["T1-P001"]

    service.link_revision(
        session,
        actor,
        experiment,
        LinkRevision(component_revision_id=revision.id, role="under test"),
    )
    service.link_revision(
        session, actor, experiment, LinkRevision(component_revision_id=revision.id)
    )  # idempotent
    assert len(experiment.revision_links) == 1 and experiment.revision_links[0].role == "under test"
    assert [e.identifier for e in service.for_revision(session, revision.id)] == ["EXP-001"]

    items, total = service.list_experiments(
        session, PageParams(limit=10, offset=0), prototype_id=prototype.id
    )
    assert total == 1 and items[0].identifier == "EXP-001"

    service.link_prototype(
        session, actor, experiment, LinkPrototype(prototype_identifier="t1-p001", role="subject")
    )
    assert len(experiment.prototype_links) == 1  # already linked
    service.unlink_prototype(session, actor, experiment, prototype)
    service.unlink_revision(session, actor, experiment, revision.id)
    assert experiment.prototype_links == [] and experiment.revision_links == []


def test_seed_creates_st36_experiments(session: Session) -> None:
    seed_n1(session)
    items, total = service.list_experiments(session, PageParams(limit=10, offset=0))
    assert total == 3
    assert sorted(e.identifier for e in items) == ["EXP-001", "EXP-002", "EXP-003"]
    exp3 = service.get_experiment(session, "EXP-003")
    assert exp3.title == "ST36 Baseline Timing" and exp3.is_placeholder
    assert seed_n1(session).created is False


def test_api_experiment_flow(client: TestClient, session: Session, actor: Actor) -> None:
    component = make_component(session, actor, "T1-MVT-006")
    revision = latest(session, component)
    created = client.post("/api/v1/experiments", json={"title": "Bench test", "objective": "Learn"})
    assert created.status_code == 201, created.text
    assert created.json()["identifier"] == "EXP-001"

    linked = client.post(
        "/api/v1/experiments/EXP-001/revisions",
        json={"component_revision_id": str(revision.id), "role": "before"},
    )
    assert (
        linked.status_code == 200
        and linked.json()["revisions"][0]["component"]["identifier"] == "T1-MVT-006"
    )

    bad = client.patch("/api/v1/experiments/EXP-001", json={"status": "COMPLETED"})
    assert bad.status_code == 422

    ok = client.patch(
        "/api/v1/experiments/EXP-001",
        json={"status": "IN_PROGRESS", "observations": "Amplitude 251"},
    )
    assert ok.status_code == 200 and ok.json()["status"] == "IN_PROGRESS"

    by_rev = client.get(f"/api/v1/revisions/{revision.id}/experiments").json()
    assert by_rev[0]["identifier"] == "EXP-001"

    assert client.delete(f"/api/v1/experiments/EXP-001/revisions/{revision.id}").status_code == 204
    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["recent_experiments"][0]["identifier"] == "EXP-001"
