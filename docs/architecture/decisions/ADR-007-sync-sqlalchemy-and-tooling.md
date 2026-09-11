# ADR-007: Synchronous SQLAlchemy, npm workspaces, and pip

**Status:** Accepted
**Date:** 2026-09-11

## Context

Several small tooling choices shape day-to-day work. They are recorded
together because each is a "boring over clever" call.

## Decisions

### Synchronous SQLAlchemy 2.0 inside FastAPI
FastAPI runs synchronous path operations in a thread pool. For a
single-user internal application with small, join-heavy queries, the
async driver stack buys nothing and costs simpler tests, simpler Alembic
integration and simpler debugging. Sessions are request-scoped via a
dependency; the service layer receives a `Session`.

Revisit when: sustained concurrent users or long-running I/O in requests.

### psycopg 3 driver
Current, maintained, supports both sync and async should we ever switch.

### Strings + check constraints for enumerations
Not native Postgres enums (see ADR-002).

### Monorepo tooling: npm workspaces and pip
* Root `package.json` declares workspaces `apps/web` and
  `packages/domain-types`. npm ships with Node; no extra package manager.
* Python uses `pyproject.toml` with `pip install -e ".[dev]"` in a venv.
  No Poetry, no uv, until dependency resolution actually becomes a
  problem.
* The backend's OpenAPI document is exported to
  `packages/domain-types/openapi.json` and compiled to TypeScript with
  `openapi-typescript`. Both are committed so the frontend builds without
  a running API.

### Lint and format
Backend: Ruff (lint), Black (format), mypy. Frontend: ESLint (flat
config, typescript-eslint, react-hooks) and Prettier. Strict TypeScript.

### Testing
Backend: pytest against a real PostgreSQL (the Compose `db` service,
separate `nemeth_test` database), migrations applied by the test session,
each test wrapped in a rolled-back transaction. Frontend: Vitest +
Testing Library. Playwright E2E is deferred until there is a flow worth
protecting end to end.

## Consequences

Anyone who knows Python and Node can run the project with two commands.
No tool in the chain is younger than five years.
