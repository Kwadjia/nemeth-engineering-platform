# Architecture Overview

## Shape

A modular monolith (ADR-001): one FastAPI backend, one React frontend, one
PostgreSQL database, engineering files on disk behind a storage interface.

```
┌──────────────────────────────┐        ┌──────────────────────────────────────┐
│  apps/web                    │  REST  │  apps/api                            │
│  React · TypeScript · Vite   │◀──────▶│  FastAPI · SQLAlchemy 2 · Pydantic 2 │
│  Tailwind · TanStack Query   │  JSON  │                                      │
│  openapi-fetch (typed client)│        │  nemeth/core     cross-cutting       │
└──────────────┬───────────────┘        │  nemeth/modules  domain modules      │
               │ types                  │  alembic/        migrations          │
┌──────────────▼───────────────┐        └───────┬───────────────────┬──────────┘
│  packages/domain-types       │                │                   │
│  openapi.json → api.d.ts     │◀───────────────┘ export            │
└──────────────────────────────┘                        ┌───────────▼──────────┐
                                                        │ PostgreSQL 16        │
                                                        └──────────────────────┘
                                                        ┌──────────────────────┐
                                                        │ storage/ (FileStorage│
                                                        │  local backend)      │
                                                        └──────────────────────┘
```

## Backend layering

```
router.py   HTTP: parse, call service, shape response. No business rules.
service.py  Domain rules, invariants, transactions. The only writer.
models.py   SQLAlchemy tables. No behaviour beyond simple properties.
schemas.py  Pydantic request/response models. The API contract.
core/       settings, db session, logging, errors, auth boundary,
            identifiers, storage, lifecycle state machine
```

Request flow: middleware assigns a request id and logs the request →
router dependency opens a `Session` and resolves the `Actor` → service
performs the operation inside the session's transaction → response is
serialised through a Pydantic schema → errors are mapped to
problem-details JSON (`application/problem+json`) with a stable `type`.

### Cross-cutting decisions

| Concern | Approach |
|---|---|
| Configuration | `pydantic-settings`, `NEMETH_*` environment variables, `.env` for local |
| Logging | stdlib `logging` with a JSON formatter; request id on every line |
| Errors | `NemethError` hierarchy → problem details; validation errors → 422 with field list |
| Auth boundary | `get_actor()` dependency returns an `Actor`; today a configured local user. Replace the dependency to add real auth. |
| Audit | `AuditMixin` (`created_at/by`, `updated_at/by`) set by the service layer from the `Actor` |
| Identity | UUID ids + human identifiers (ADR-005) |
| Files | `FileStorage` interface (ADR-003) |
| Lifecycle | One `LifecycleState` enum and transition table in `core/lifecycle.py` |

## Frontend structure

```
src/
  app/          router, layout shell, navigation, providers
  components/ui shadcn-style primitives (button, badge, table, card, …)
  components/   domain components (lifecycle badge, identifier, bom tree)
  features/     one folder per navigation area (dashboard, products, …)
  lib/          api client (openapi-fetch), formatting, query keys
  styles/       tokens and global CSS
```

The frontend never invents domain logic: it displays what the API returns
and posts what the API accepts. Types come from `@nemeth/domain-types`,
generated from the backend's OpenAPI document.

## Data flow for the core concepts

* **Product → Model → root assembly.** A model's BOM is the resolved BOM of
  its root assembly component's revision.
* **Caliber → root assembly.** Same mechanism; the movement assembly is a
  component like any other, so movement and case share one BOM engine.
* **Component → revisions.** Content lives on revisions. Creating a
  revision copies the source. Frozen revisions are immutable (ADR-004).
* **Assembly revision → BOM lines → child components (+ pins).** Resolved
  at query time by mode (ADR-006).

## Environments

| | Local (Docker Compose) | Later |
|---|---|---|
| Database | `db` service, volume `pgdata` | managed PostgreSQL |
| Files | `./storage` bind mount | S3 / Azure Blob via `FileStorage` |
| API | `api` service, uvicorn reload | container on a small VM |
| Web | `web` service, Vite dev server with `/api` proxy | static build behind the API or a CDN |

## Non-goals for now

Kubernetes, message brokers, caches, search engines, multi-tenant auth,
microservices. Each is a future ADR if and when a measured need appears.
