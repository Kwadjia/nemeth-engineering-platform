"""Human identifiers and revision labels (ADR-005, docs/architecture/identifiers.md).

Identifiers are minted from a per-prefix counter row updated atomically with
``INSERT … ON CONFLICT DO UPDATE … RETURNING``. If a hand-assigned identifier already
occupies the next number, the counter simply advances past it.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from sqlalchemy import Integer, String, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from nemeth.core.db import Base
from nemeth.core.errors import DomainValidationError

IDENTIFIER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{1,62}$")


class IdentifierCounter(Base):
    __tablename__ = "identifier_counters"

    prefix: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


def normalize_identifier(value: str) -> str:
    """Uppercase, trimmed, validated. Raises ``DomainValidationError`` when malformed."""
    candidate = value.strip().upper()
    if not IDENTIFIER_PATTERN.match(candidate):
        raise DomainValidationError(
            "Identifiers must be 2-63 characters of A-Z, 0-9, '.' or '-' and start with a letter or digit.",
            field="identifier",
            value=value,
        )
    return candidate


def _bump(session: Session, prefix: str) -> int:
    stmt = (
        insert(IdentifierCounter)
        .values(prefix=prefix, last_value=1)
        .on_conflict_do_update(
            index_elements=[IdentifierCounter.prefix],
            set_={"last_value": IdentifierCounter.last_value + 1},
        )
        .returning(IdentifierCounter.last_value)
    )
    return int(session.execute(stmt).scalar_one())


def next_identifier(
    session: Session,
    prefix: str,
    *,
    exists: Callable[[str], bool],
    width: int = 3,
    separator: str = "-",
) -> str:
    """Return the next free ``{prefix}{separator}{NNN}``.

    ``exists`` is consulted so that manually assigned identifiers never collide with
    generated ones; the counter advances until it finds a free number.
    """
    prefix = normalize_identifier(prefix)
    for _ in range(10_000):
        value = _bump(session, prefix)
        candidate = f"{prefix}{separator}{value:0{width}d}"
        if not exists(candidate):
            return candidate
    raise RuntimeError(f"Could not allocate an identifier for prefix {prefix!r}")


def ensure_counter_at_least(session: Session, prefix: str, value: int) -> None:
    """Move a prefix counter forward (never backward). Used after hand-assigned identifiers."""
    prefix = normalize_identifier(prefix)
    stmt = (
        insert(IdentifierCounter)
        .values(prefix=prefix, last_value=value)
        .on_conflict_do_update(
            index_elements=[IdentifierCounter.prefix],
            set_={"last_value": func.greatest(IdentifierCounter.last_value, value)},
        )
    )
    session.execute(stmt)


def revision_label(number: int) -> str:
    """1 → A, 26 → Z, 27 → AA, 28 → AB … (PLM convention)."""
    if number < 1:
        raise ValueError("revision numbers start at 1")
    label = ""
    n = number
    while n > 0:
        n, rem = divmod(n - 1, 26)
        label = chr(ord("A") + rem) + label
    return label
