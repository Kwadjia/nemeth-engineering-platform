"""Audit stamping helpers used by every service that writes."""

from __future__ import annotations

from typing import Any

from nemeth.core.auth import Actor


def stamp_created(entity: Any, actor: Actor) -> None:
    entity.created_by = actor.audit_id
    entity.updated_by = actor.audit_id


def stamp_updated(entity: Any, actor: Actor) -> None:
    entity.updated_by = actor.audit_id
