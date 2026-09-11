# NEMETH Engineering Platform

Internal product-development and engineering operating system for
**NEMETH — Detroit**, an independent mechanical watch company. The platform
is a lightweight PLM: product definition, components with immutable
revisions, recursive bills of materials, and (in coming slices) prototypes,
experiments, measurements, serialized watch genealogy, documents, suppliers
and engineering changes.

First flagship product: **NEMETH N1**. First in-house movement: **Caliber N1**.

> Modern American engineering combined with traditional mechanical
> watchmaking. Understated, premium, mechanical, architectural.

**Current milestone:** v0.1 — see [`docs/architecture/plan.md`](docs/architecture/plan.md).

## Quick start

Prerequisites: Docker Desktop, Node 20+, Python 3.11+.

```bash
cp .env.example .env
docker compose up -d db                    # PostgreSQL 16 (+ nemeth_test database)

# API
cd apps/api
python -m venv .venv && . .venv/Scripts/activate      # Windows; bin/activate elsewhere
pip install -e ".[dev]"
python -m nemeth db upgrade                # apply migrations
python -m nemeth seed                      # NEMETH N1 placeholder data (idempotent)
python -m nemeth serve                     # http://localhost:8000/api/v1/docs

# Web (new terminal, repository root)
npm install
npm run dev                                # http://localhost:5173
```

Or run the whole stack in containers: `docker compose up` (db, api with
auto-migrations, web dev server). See
[`docs/development/local-setup.md`](docs/development/local-setup.md).

## Repository layout

```
apps/
  api/            FastAPI · SQLAlchemy 2 · Alembic · pytest      (Python)
  web/            React · TypeScript · Vite · Tailwind · Vitest  (Node)
packages/
  domain-types/   TypeScript types generated from the API's OpenAPI document
docs/
  architecture/   plan, overview, identifiers, future capabilities, decisions/ (ADRs)
  domain/         domain model and traceability questions
  development/    local setup, conventions
  manufacturing/  manufacturing concepts (planned)
storage/          engineering files on disk (cad, drawings, photos, …) — data, not code
scripts/          helper scripts (database init)
docker-compose.yml
```

## Architecture in one paragraph

A modular monolith (ADR-001): one FastAPI backend organised by domain
module, one React frontend, one PostgreSQL database (ADR-002), files on
disk behind a storage interface (ADR-003). Components carry identity;
revisions carry engineering content and become immutable once anything
physical can depend on them (ADR-004). Every record has a UUID and a
separate human identifier such as `N1-MVT-002` (ADR-005). BOM lines belong
to an assembly revision and reference a child component with an optional
pinned revision, resolved at query time as *latest* or *released*
(ADR-006). Details: [`docs/architecture/overview.md`](docs/architecture/overview.md),
[`docs/domain/domain-model.md`](docs/domain/domain-model.md),
[`docs/architecture/decisions/`](docs/architecture/decisions/).

## Quality gates

| | Command (from the directory shown) |
|---|---|
| API tests | `apps/api$ pytest` (needs the `db` container) |
| API lint / format / types | `apps/api$ ruff check . && black --check . && mypy nemeth` |
| Web typecheck / build | `$ npm run typecheck && npm run build` |
| Web lint / format | `$ npm run lint && npm run format:check` |
| Web tests | `$ npm run test` |
| Regenerate API types | `$ npm run api:types` |

## Status

Implemented in v0.1 so far: repository and architecture, Docker Compose,
PostgreSQL schema and migrations, FastAPI application, React shell,
Products / Models / Calibers, Components with immutable revisions,
recursive BOMs with pinned or floating resolution and where-used, Prototypes
with part instances and append-only build records (derived as-built
configuration), N1 seed data, tests. Planned next: Experiments,
Measurements, serialized Watches, Documents, Suppliers, Engineering Changes.

All seed data is marked **placeholder** in the database and in the UI.
