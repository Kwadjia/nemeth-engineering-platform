"""Lifecycle states shared by products, models, calibers and component revisions.

See ADR-004 for the reasoning behind the frozen threshold.
"""

from __future__ import annotations

from enum import StrEnum

from nemeth.core.errors import InvalidTransitionError


class LifecycleState(StrEnum):
    CONCEPT = "CONCEPT"
    DESIGN = "DESIGN"
    PROTOTYPE = "PROTOTYPE"
    VALIDATION = "VALIDATION"
    RELEASED = "RELEASED"
    OBSOLETE = "OBSOLETE"


ORDERED_STATES: tuple[LifecycleState, ...] = (
    LifecycleState.CONCEPT,
    LifecycleState.DESIGN,
    LifecycleState.PROTOTYPE,
    LifecycleState.VALIDATION,
    LifecycleState.RELEASED,
    LifecycleState.OBSOLETE,
)

#: States in which a revision's engineering content is immutable.
FROZEN_STATES: frozenset[LifecycleState] = frozenset(
    {
        LifecycleState.PROTOTYPE,
        LifecycleState.VALIDATION,
        LifecycleState.RELEASED,
        LifecycleState.OBSOLETE,
    }
)

ALLOWED_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.CONCEPT: frozenset({LifecycleState.DESIGN, LifecycleState.OBSOLETE}),
    LifecycleState.DESIGN: frozenset(
        {LifecycleState.CONCEPT, LifecycleState.PROTOTYPE, LifecycleState.OBSOLETE}
    ),
    LifecycleState.PROTOTYPE: frozenset({LifecycleState.VALIDATION, LifecycleState.OBSOLETE}),
    LifecycleState.VALIDATION: frozenset({LifecycleState.RELEASED, LifecycleState.OBSOLETE}),
    LifecycleState.RELEASED: frozenset({LifecycleState.OBSOLETE}),
    LifecycleState.OBSOLETE: frozenset(),
}


def is_frozen(state: LifecycleState) -> bool:
    return state in FROZEN_STATES


def can_transition(current: LifecycleState, target: LifecycleState) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def assert_transition(current: LifecycleState, target: LifecycleState) -> None:
    if not can_transition(current, target):
        allowed = ", ".join(sorted(s.value for s in ALLOWED_TRANSITIONS[current])) or "none"
        raise InvalidTransitionError(
            f"Cannot transition from {current.value} to {target.value}. Allowed: {allowed}.",
            current=current.value,
            target=target.value,
        )
