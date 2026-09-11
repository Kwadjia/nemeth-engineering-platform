"""Resolve a path reference that may be either a UUID or a human identifier."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from nemeth.core.errors import NotFoundError


class HasIdentity(Protocol):
    id: Any
    identifier: Any


T = TypeVar("T", bound=HasIdentity)


def parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def get_by_ref(
    session: Session,
    model: type[T],
    ref: str,
    *,
    options: Sequence[Any] = (),
    label: str | None = None,
) -> T:
    """Fetch ``model`` by UUID or by (case-insensitive) identifier, or raise 404."""
    stmt = select(model)
    as_uuid = parse_uuid(ref)
    if as_uuid is not None:
        stmt = stmt.where(model.id == as_uuid)
    else:
        stmt = stmt.where(model.identifier == ref.strip().upper())
    for opt in options:
        stmt = stmt.options(opt)
    result = session.execute(stmt).unique().scalar_one_or_none()
    if result is None:
        name = label or getattr(model, "__name__", "record")
        raise NotFoundError(f"{name} {ref!r} not found", resource=name, ref=ref)
    return result
