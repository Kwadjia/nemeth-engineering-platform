# Architecture Decision Records

Meaningful architectural decisions are recorded here, one file each, in
the order they were made. A decision is "meaningful" when reversing it
later would cost more than a day, or when a future reader would otherwise
ask "why on earth did they do that?".

| ADR | Title | Status |
|---|---|---|
| [001](ADR-001-modular-monolith.md) | Modular monolith | Accepted |
| [002](ADR-002-postgresql.md) | PostgreSQL as the system of record | Accepted |
| [003](ADR-003-files-outside-database.md) | Engineering files live outside the database | Accepted |
| [004](ADR-004-immutable-component-revisions.md) | Immutable component revisions with a frozen threshold | Accepted |
| [005](ADR-005-uuid-and-human-identifiers.md) | UUID primary keys and separate human identifiers | Accepted |
| [006](ADR-006-bom-lines-on-assembly-revisions.md) | BOM lines belong to an assembly revision, with optional pins | Accepted |
| [007](ADR-007-sync-sqlalchemy-and-tooling.md) | Synchronous SQLAlchemy, npm workspaces, and pip | Accepted |

## Template

```markdown
# ADR-NNN: Title

**Status:** Proposed | Accepted | Superseded by ADR-MMM
**Date:** YYYY-MM-DD

## Context
What situation forces a decision? What constraints apply?

## Decision
What we are doing, stated plainly.

## Consequences
What becomes easier, what becomes harder, what we will revisit and when.
```
