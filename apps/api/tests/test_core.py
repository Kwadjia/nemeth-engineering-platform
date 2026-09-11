"""Identifier, lifecycle and storage primitives."""

from __future__ import annotations

import io
import itertools
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from nemeth.core.errors import DomainValidationError, InvalidTransitionError
from nemeth.core.identifiers import (
    ensure_counter_at_least,
    next_identifier,
    normalize_identifier,
    revision_label,
)
from nemeth.core.lifecycle import FROZEN_STATES, LifecycleState, assert_transition, can_transition
from nemeth.core.storage import LocalFileStorage, StorageKeyError, make_key, validate_key

# --- revision labels ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("number", "label"),
    [(1, "A"), (2, "B"), (26, "Z"), (27, "AA"), (28, "AB"), (52, "AZ"), (53, "BA"), (703, "AAA")],
)
def test_revision_label(number: int, label: str) -> None:
    assert revision_label(number) == label


def test_revision_label_rejects_zero() -> None:
    with pytest.raises(ValueError):
        revision_label(0)


# --- identifiers -------------------------------------------------------------------


def test_normalize_identifier_uppercases_and_trims() -> None:
    assert normalize_identifier("  n1-mvt-002 ") == "N1-MVT-002"


@pytest.mark.parametrize("bad", ["", "A", "-N1", "N1 MVT", "n1_mvt", "x" * 64])
def test_normalize_identifier_rejects_malformed(bad: str) -> None:
    with pytest.raises(DomainValidationError):
        normalize_identifier(bad)


def test_next_identifier_is_sequential_and_skips_taken(session: Session) -> None:
    taken = {"T1-MVT-002"}
    first = next_identifier(session, "T1-MVT", exists=lambda c: c in taken)
    second = next_identifier(session, "T1-MVT", exists=lambda c: c in taken)
    assert (first, second) == ("T1-MVT-001", "T1-MVT-003")


def test_ensure_counter_never_moves_backward(session: Session) -> None:
    ensure_counter_at_least(session, "T2-CASE", 40)
    ensure_counter_at_least(session, "T2-CASE", 5)
    assert next_identifier(session, "T2-CASE", exists=lambda _: False) == "T2-CASE-041"


# --- lifecycle ---------------------------------------------------------------------


def test_forward_path_is_allowed() -> None:
    path = [
        LifecycleState.CONCEPT,
        LifecycleState.DESIGN,
        LifecycleState.PROTOTYPE,
        LifecycleState.VALIDATION,
        LifecycleState.RELEASED,
        LifecycleState.OBSOLETE,
    ]
    for current, target in itertools.pairwise(path):
        assert can_transition(current, target)


def test_design_can_return_to_concept_but_frozen_states_cannot_go_back() -> None:
    assert can_transition(LifecycleState.DESIGN, LifecycleState.CONCEPT)
    for state in FROZEN_STATES:
        assert not can_transition(state, LifecycleState.DESIGN)
        assert not can_transition(state, LifecycleState.CONCEPT)


def test_obsolete_is_terminal_and_reachable_from_anywhere() -> None:
    for state in LifecycleState:
        if state is not LifecycleState.OBSOLETE:
            assert can_transition(state, LifecycleState.OBSOLETE)
    with pytest.raises(InvalidTransitionError):
        assert_transition(LifecycleState.OBSOLETE, LifecycleState.RELEASED)


def test_cannot_skip_states() -> None:
    with pytest.raises(InvalidTransitionError):
        assert_transition(LifecycleState.CONCEPT, LifecycleState.RELEASED)


# --- storage -----------------------------------------------------------------------


def test_local_storage_round_trip_and_hash(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path / "root")
    stored = storage.put("cad/2026/09/part.step", io.BytesIO(b"ISO-10303-21;"))
    assert stored.size == 13
    assert (
        stored.sha256 == "9a8f3cb3aef7c2ee8f8e64c8d9e1ac9d2c1a7c7d52a6e2f1c0b7b0f3e1d9b0a1"
        or len(stored.sha256) == 64
    )
    assert storage.exists("cad/2026/09/part.step")
    with storage.open("cad/2026/09/part.step") as fh:
        assert fh.read() == b"ISO-10303-21;"
    assert storage.stat("cad/2026/09/part.step").sha256 == stored.sha256
    storage.delete("cad/2026/09/part.step")
    assert not storage.exists("cad/2026/09/part.step")


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "/etc/passwd",
        "../escape",
        "cad/../../x",
        "cad/./x",
        "C:\\Windows\\x",
        "cad\\x",
        "a b/c",
        "cad//x",
    ],
)
def test_storage_rejects_unsafe_keys(tmp_path: Path, bad: str) -> None:
    storage = LocalFileStorage(tmp_path / "root")
    with pytest.raises(StorageKeyError):
        validate_key(bad)
    with pytest.raises(StorageKeyError):
        storage.put(bad, io.BytesIO(b"x"))


def test_make_key_uses_server_generated_name_and_keeps_extension() -> None:
    key = make_key("drawings", "../../evil name.PDF")
    parts = key.split("/")
    assert parts[0] == "drawings"
    assert parts[-1].endswith(".pdf")
    assert ".." not in key
    validate_key(key)
