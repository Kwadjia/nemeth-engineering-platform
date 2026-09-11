"""Authentication boundary.

Today there is exactly one actor: the local user named in settings. Every write path
receives an ``Actor`` through this dependency and records it in ``created_by`` /
``updated_by``. Adding real authentication later means replacing ``get_actor`` with a
token-validating dependency and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from nemeth.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class Actor:
    id: str
    display_name: str

    @property
    def audit_id(self) -> str:
        return self.id


def get_actor(settings: Settings = Depends(get_settings)) -> Actor:
    return Actor(id=settings.actor_id, display_name=settings.actor_name)


SYSTEM_ACTOR = Actor(id="system", display_name="System")
