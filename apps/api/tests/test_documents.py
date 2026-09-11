"""Attachments: validation, hashing, duplicate detection, storage safety, HTTP flow."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nemeth.core.auth import Actor
from nemeth.core.errors import ConflictError, DomainValidationError, NotFoundError
from nemeth.core.pagination import PageParams
from nemeth.core.storage import LocalFileStorage
from nemeth.main import create_app
from nemeth.modules.documents import service
from nemeth.modules.documents.models import AttachmentKind
from nemeth.modules.documents.schemas import AttachmentUpdate
from tests.factories import latest, make_component

STEP = b"ISO-10303-21;\nHEADER;\nENDSEC;\nEND-ISO-10303-21;\n"


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(tmp_path / "storage")


def _upload(
    session: Session,
    actor: Actor,
    storage: LocalFileStorage,
    entity_type: str,
    entity_id,
    name: str,
    data: bytes,
    kind: AttachmentKind = AttachmentKind.CAD,
):
    return service.upload_attachment(
        session,
        actor,
        storage,
        entity_type=entity_type,
        entity_id=entity_id,
        kind=kind,
        filename=name,
        stream=io.BytesIO(data),
        declared_mime=None,
        description=None,
    )


def test_upload_hashes_and_stores_under_a_server_key(
    session: Session, actor: Actor, storage: LocalFileStorage
) -> None:
    component = make_component(session, actor, "T1-MVT-002", "Mainplate")
    revision = latest(session, component)
    attachment = _upload(
        session,
        actor,
        storage,
        "component_revision",
        revision.id,
        "../../Mainplate Rev A.STEP",
        STEP,
    )
    assert attachment.identifier == "DOC-00001"
    assert attachment.original_filename == "Mainplate Rev A.STEP"
    assert attachment.sha256 == hashlib.sha256(STEP).hexdigest()
    assert attachment.size_bytes == len(STEP)
    assert attachment.stored_key.startswith("cad/") and attachment.stored_key.endswith(".step")
    assert ".." not in attachment.stored_key
    assert storage.exists(attachment.stored_key)
    assert b"".join(service.open_content(storage, attachment)) == STEP
    ref = service.resolve_entity(session, "component_revision", revision.id)
    assert ref.identifier == "T1-MVT-002 Rev A" and ref.label == "Mainplate"


def test_identical_content_on_same_entity_is_reported_not_duplicated(
    session: Session, actor: Actor, storage: LocalFileStorage
) -> None:
    component = make_component(session, actor, "T1-MVT-002")
    first = _upload(session, actor, storage, "component", component.id, "plate.step", STEP)
    with pytest.raises(ConflictError) as excinfo:
        _upload(session, actor, storage, "component", component.id, "plate-copy.step", STEP)
    assert excinfo.value.extra["existing_identifier"] == first.identifier
    # The rejected upload leaves no file behind.
    assert list(storage.iter_keys()) == [first.stored_key]
    # Changed content is a new attachment.
    second = _upload(session, actor, storage, "component", component.id, "plate.step", STEP + b"x")
    assert second.sha256 != first.sha256


@pytest.mark.parametrize("name", ["evil.exe", "script.sh", "noext", "archive.tar.gz"])
def test_disallowed_extensions_are_rejected(
    session: Session, actor: Actor, storage: LocalFileStorage, name: str
) -> None:
    component = make_component(session, actor, "T1-MVT-002")
    with pytest.raises(DomainValidationError):
        _upload(session, actor, storage, "component", component.id, name, b"x")
    assert list(storage.iter_keys()) == []


def test_empty_file_unknown_entity_and_bad_type(
    session: Session, actor: Actor, storage: LocalFileStorage
) -> None:
    component = make_component(session, actor, "T1-MVT-002")
    with pytest.raises(DomainValidationError):
        _upload(session, actor, storage, "component", component.id, "empty.csv", b"")
    with pytest.raises(NotFoundError):
        _upload(session, actor, storage, "prototype", component.id, "x.csv", b"1,2")
    with pytest.raises(DomainValidationError):
        _upload(session, actor, storage, "spaceship", component.id, "x.csv", b"1,2")


def test_update_list_and_delete(session: Session, actor: Actor, storage: LocalFileStorage) -> None:
    component = make_component(session, actor, "T1-MVT-002")
    a = _upload(
        session,
        actor,
        storage,
        "component",
        component.id,
        "photo.jpg",
        b"\xff\xd8\xff",
        AttachmentKind.PHOTO,
    )
    b = _upload(
        session,
        actor,
        storage,
        "component",
        component.id,
        "cert.pdf",
        b"%PDF-1.4",
        AttachmentKind.CERTIFICATE,
    )
    service.update_attachment(
        session, actor, a, AttachmentUpdate(description="Bench photo", kind=AttachmentKind.PHOTO)
    )
    assert a.description == "Bench photo" and a.mime_type == "image/jpeg"
    _items, total = service.list_attachments(
        session, PageParams(limit=10, offset=0), entity_type="component", entity_id=component.id
    )
    assert total == 2
    photos, _ = service.list_attachments(
        session, PageParams(limit=10, offset=0), kind=AttachmentKind.PHOTO
    )
    assert [x.id for x in photos] == [a.id]
    key = b.stored_key
    service.delete_attachment(session, storage, b)
    assert not storage.exists(key)
    assert service.count_by_kind(session)["PHOTO"] == 1


def test_api_upload_download_and_policy(
    session: Session, actor: Actor, storage: LocalFileStorage
) -> None:
    from nemeth.core.db import get_session

    app = create_app()

    def _override():
        yield session
        session.flush()

    app.dependency_overrides[get_session] = _override
    app.dependency_overrides[service.get_storage] = lambda: storage
    component = make_component(session, actor, "T1-MVT-002")

    with TestClient(app) as client:
        policy = client.get("/api/v1/attachments/policy").json()
        assert (
            ".step" in policy["allowed_extensions"]
            and "component_revision" in policy["entity_types"]
        )

        uploaded = client.post(
            "/api/v1/attachments",
            data={
                "entity_type": "component",
                "entity_id": str(component.id),
                "kind": "DRAWING",
                "description": "Sheet 1",
            },
            files={"file": ("mainplate.pdf", b"%PDF-1.4 drawing", "application/pdf")},
        )
        assert uploaded.status_code == 201, uploaded.text
        body = uploaded.json()
        assert body["identifier"] == "DOC-00001" and body["kind"] == "DRAWING"

        again = client.post(
            "/api/v1/attachments",
            data={"entity_type": "component", "entity_id": str(component.id), "kind": "DRAWING"},
            files={"file": ("mainplate.pdf", b"%PDF-1.4 drawing", "application/pdf")},
        )
        assert again.status_code == 409 and again.json()["existing_identifier"] == "DOC-00001"

        bad = client.post(
            "/api/v1/attachments",
            data={"entity_type": "component", "entity_id": str(component.id)},
            files={"file": ("virus.exe", b"MZ", "application/octet-stream")},
        )
        assert bad.status_code == 422

        content = client.get("/api/v1/attachments/DOC-00001/content")
        assert content.status_code == 200
        assert content.content == b"%PDF-1.4 drawing"
        assert content.headers["content-type"].startswith("application/pdf")
        assert "mainplate.pdf" in content.headers["content-disposition"]
        assert (
            content.headers["x-content-sha256"] == hashlib.sha256(b"%PDF-1.4 drawing").hexdigest()
        )

        listed = client.get(
            "/api/v1/attachments",
            params={"entity_type": "component", "entity_id": str(component.id)},
        ).json()
        assert listed["total"] == 1 and listed["items"][0]["entity"]["identifier"] == "T1-MVT-002"

        assert client.delete("/api/v1/attachments/DOC-00001").status_code == 204
        assert client.get("/api/v1/attachments/DOC-00001").status_code == 404
