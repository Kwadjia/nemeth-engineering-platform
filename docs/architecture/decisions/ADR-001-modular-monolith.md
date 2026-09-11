# ADR-001: Modular monolith

**Status:** Accepted
**Date:** 2026-09-11

## Context

The platform is a single-user internal application today and must be able
to grow into the operating system of a small manufacture. The temptation
with PLM/MES-shaped systems is to start with services per concern
(documents, BOM, quality, …). The team is one engineer.

## Decision

Build one deployable backend (FastAPI) and one frontend (React), sharing
one PostgreSQL database. Organise the backend by **domain module** under
`apps/api/nemeth/modules/`:

```
modules/
  products/     Product, ProductModel, Caliber
  components/   Component, ComponentRevision, lifecycle
  bom/          BomLine, resolution, where-used
  (later) prototypes/ experiments/ testing/ watches/ documents/ suppliers/ changes/
```

Each module owns `models.py` (SQLAlchemy), `schemas.py` (Pydantic),
`service.py` (domain rules; the only place that writes) and `router.py`
(HTTP). Modules may import other modules' models and services. Modules
never import other modules' routers. Cross-cutting concerns live in
`nemeth/core/` (settings, db, logging, errors, auth boundary, identifiers,
storage).

## Consequences

* One process to run, test, migrate and back up.
* Domain rules are testable without HTTP.
* If a module ever needs to become a service, its boundary is already
  explicit: service functions and models, not shared tables across
  modules' private state.
* No Kubernetes, Kafka, message brokers, Redis, Elasticsearch or cloud
  services until a demonstrated need exists. A demonstrated need means a
  measured problem, not a feature idea.
