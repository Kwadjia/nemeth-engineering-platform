# NEMETH Engineering Platform — v0.1 Plan

**Milestone:** NEMETH Engineering Platform v0.1
**Status:** in progress
**Owner:** Arthur Nemeth
**Last updated:** 2026-09-11

## Purpose

An internal product-development and engineering operating system for NEMETH,
an independent mechanical watch company in Detroit, Michigan. It is a
lightweight combination of PLM, requirements, BOM management, revision
control, manufacturing documentation, experiment logging, test data,
serial-number genealogy and, eventually, a digital thread for every watch.

The first flagship product is the **NEMETH N1**. The first in-house movement
is **Caliber N1**.

## First principles

1. **Do not overengineer.** Single-user internal application today; a small
   independent manufacture tomorrow. Build the foundation, not the future.
2. **Boring technology.** Modular monolith, PostgreSQL, REST, files on disk.
   No Kubernetes, Kafka, microservices, Redis, Elasticsearch or cloud
   infrastructure until a demonstrated need exists.
3. **Traceability is the product.** Every schema decision is judged against
   the traceability questions in
   [`docs/domain/domain-model.md`](../domain/domain-model.md#traceability-questions).
4. **Never overwrite engineering history.** Revisions are immutable once
   anything physical can depend on them.
5. **Vertical slices, always runnable.** Each slice ships schema, API, UI,
   tests and docs together.

## Scope of v0.1

| # | Slice | Status |
|---|-------|--------|
| 1 | Repository, architecture docs, Docker Compose, PostgreSQL, FastAPI, React shell | ✅ done |
| 2 | Products, Models, Calibers | ✅ done |
| 3 | Components + immutable revisions | ✅ done |
| 4 | Recursive BOMs (design BOM, pinned/floating resolution, where-used) | ✅ done |
| 5 | N1 seed data (clearly marked placeholder) | ✅ done (product/caliber/components; prototype + experiment seeds arrive with their slices) |
| 6 | Tests: revision immutability, recursive BOM | ✅ done |
| 7 | Prototypes, part instances, build records (physical genealogy, ADR-008) | ✅ done |
| 8 | Experiments (lab notebook, links to prototypes and revisions) | ✅ done |
| 9 | Measurements / test records (test-type registry, timegrapher summaries) | ✅ done |
| 10 | Serialized watches / build genealogy | ⬜ next |
| 11 | Documents / attachments (SHA-256, local storage backend) | ⬜ |
| 12 | Suppliers, Engineering Changes (lightweight) | ⬜ |

Out of scope for v0.1: MES, travelers, CAD integration, calculators, AI
assistant, e-commerce, customer ownership, public provenance pages. Paths
for these are recorded in
[`docs/architecture/future-capabilities.md`](future-capabilities.md).

## Architecture summary

```
apps/web  (React + TypeScript + Vite + Tailwind)  ──REST/JSON──▶  apps/api (FastAPI)
                                                                     │
                                          packages/domain-types ◀── OpenAPI
                                                                     │
                                                              PostgreSQL 16
                                                                     │
                                                         storage/ (files on disk,
                                                          behind a storage interface)
```

* **Modular monolith** (ADR-001). One FastAPI process, one database, one
  deployable. Code is organised by domain module under
  `apps/api/nemeth/modules/*`; each module owns its models, schemas,
  service and router. Modules may import each other's *services and
  models*, never each other's routers.
* **PostgreSQL** (ADR-002) is the system of record. UUID primary keys,
  human identifiers as separate unique columns (ADR-005).
* **Files outside the database** (ADR-003) behind a `FileStorage`
  interface with a local-filesystem backend today and S3/Azure Blob later.
* **Immutable component revisions** (ADR-004) with a small, explicit
  lifecycle state machine.
* **BOM lines belong to an assembly revision** and reference a child
  component with an optional pinned child revision (ADR-006).
* **Synchronous SQLAlchemy 2.0** inside FastAPI (ADR-007). Simpler tests,
  simpler migrations, adequate for an internal tool.

See [`overview.md`](overview.md) for the layered structure and request
flow, and [`decisions/`](decisions/) for the ADRs.

## Implementation checklist — first task

### Foundation
- [x] Monorepo skeleton (`apps/`, `packages/`, `docs/`, `storage/`, `scripts/`)
- [x] `.gitignore`, `.editorconfig`, `.gitattributes`
- [x] `docker-compose.yml` (db, api, web) and `.env.example`
- [x] PostgreSQL 16 service with healthcheck and persistent volume
- [x] FastAPI app: settings, structured JSON logging, request-id middleware,
      problem-details error responses, health endpoint, auth boundary (`Actor`)
- [x] SQLAlchemy 2.0 typed models, naming conventions, audit mixin
- [x] Alembic configured; initial migration `0001_core_plm`
- [x] Identifier counters + revision label helpers
- [x] `FileStorage` interface + `LocalFileStorage` with path-safety checks
- [x] React shell: routing, layout, navigation, brand tokens, UI primitives
- [x] OpenAPI → TypeScript types in `packages/domain-types`
- [x] Lint/format: Ruff + Black + mypy; ESLint + Prettier; strict TS

### Domain — Products
- [x] `Product`, `ProductModel`, `Caliber` models + schemas + services
- [x] REST: list/get/create/update products; models under products; calibers
- [x] Caliber specification fields (typed) + `specification` JSONB extension
- [x] UI: Products list/detail, Calibers list/detail

### Domain — Components & revisions
- [x] `Component` (identity) + `ComponentRevision` (engineering content)
- [x] Revision creation copies content from the source revision; labels A…Z, AA…
- [x] Lifecycle state machine; revisions frozen from PROTOTYPE onward
- [x] Editing/deleting frozen content → 409 Conflict
- [x] REST: components, revisions, transitions
- [x] UI: Components table with filters; component detail; revision detail;
      create/edit forms; state transitions

### Domain — BOM
- [x] `BomLine` on assembly revisions (child component + optional pinned revision)
- [x] Cycle detection; part-vs-assembly invariant; find-number uniqueness
- [x] Resolution modes: `latest` and `released`
- [x] Tree and flat (indented, level, path, extended qty) views
- [x] Where-used for a component / a revision
- [x] UI: BOM explorer (tree + flat), pin indicator

### Domain — Prototypes (slice 7)
- [x] `Prototype` register with forward-only status (PLANNED → BUILDING → ACTIVE → RETIRED)
- [x] `PartInstance`: one physical part against an exact **frozen** revision; serial, lot,
      source, material/heat-treatment lots; `PI-NNNNN`
- [x] `BuildRecord` (append-only, `BR-NNNNN`) with ordered INSTALL/REMOVE entries
- [x] Derived current configuration; physical where-used (revision → prototypes)
- [x] REST: prototypes, configuration, builds, part-instances, component instances
- [x] UI: Prototypes list/detail (configuration, build log, new build), Part instances,
      component detail instances panel, dashboard active prototype
- [x] Seed: N1-P001 (planned, placeholder); seed is idempotent per record
- [x] Tests: identifiers, frozen-revision rule, install/remove/salvage history,
      configuration derivation, retired prototypes, API flow

### Domain — Experiments (slice 8)
- [x] `Experiment` (`EXP-NNN`): notebook sections (objective, hypothesis, configuration,
      methodology, equipment, procedure, observations, results, conclusion, follow-up),
      status PLANNED → IN_PROGRESS → COMPLETED | ABANDONED, outcome
- [x] Links to prototypes and component revisions with a free-text role
- [x] REST: experiments CRUD, link/unlink, by prototype, by revision
- [x] UI: Experiments list, notebook page with editor, links panel; prototype experiments
      panel; dashboard recent experiments
- [x] Seed: EXP-001 ST36 disassembly, EXP-002 reassembly, EXP-003 baseline timing
- [x] Tests: identifiers, status flow, links, seed, API flow

### Domain — Testing (slice 9)
- [x] `TestType` registry rows (code, metric list with units, custom-metrics flag,
      positions flag); nine built-ins installed by the seed; new types via POST
- [x] `TestRun` (`TR-NNNNN`): type, at most one subject (prototype / part instance /
      revision), optional experiment, performed at/by, equipment, conditions JSON, outcome
- [x] `Measurement` long format: metric, value, unit (defaulted from the type), position,
      recorded_at, notes, extra; validated against the type
- [x] Timegrapher summary: per-position rate/amplitude/beat error, mean, delta,
      amplitude range, max beat error, lift angle
- [x] REST: test types, test runs, append measurements, by prototype/experiment/part,
      prototype latest timing, dashboard latest timing
- [x] UI: Testing list, new-run form (six-position grid for timegrapher, generic rows
      otherwise), run detail with timing table, prototype and experiment panels, dashboard
- [x] Tests: built-ins, timing maths, metric/position validation, custom types,
      subject rule, API flow; Vitest timing table

### Seed & tests & docs
- [x] `python -m nemeth seed` — idempotent N1 seed, marked as placeholder
- [x] pytest: revision immutability, revision copy, state machine, BOM tree,
      cycle rejection, where-used, identifier counters, storage path safety
- [x] Vitest: BOM tree rendering, identifier/format helpers
- [x] README, overview, domain model, identifiers, local setup, ADRs

## Working agreement

After each slice: `pytest`, `ruff`, `black --check`, `mypy`,
`alembic upgrade head` on a clean database, `npm run build`, `npm run lint`,
`npm run test`, then update docs. Every slice should be one reviewable
commit or a short series of them.
