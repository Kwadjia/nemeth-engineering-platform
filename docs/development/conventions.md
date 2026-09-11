# Development Conventions

## Working in slices

Each slice ships schema, migration, service rules, API, UI, tests and docs
together and leaves the repository runnable. After a slice:

1. `pytest` · `ruff check .` · `black --check .` · `mypy nemeth`
2. `npm run typecheck` · `npm run lint` · `npm run test` · `npm run build`
3. `npm run api:types` if any schema changed; commit the generated files
4. Update `docs/architecture/plan.md` and the domain model if concepts moved
5. Record any decision with long-term consequences as an ADR

## Backend

* **Layers.** `router` parses and shapes; `service` decides and writes;
  `models` describe tables; `schemas` describe the API. Business rules never
  live in routers or models.
* **Writes go through relationships.** Add with `parent.children.append(x)`,
  remove with `parent.children.remove(x)`; do not `session.delete` an
  object that lives in a loaded collection. This keeps in-memory state
  correct within a request and within tests.
* **Errors are typed.** Raise `NemethError` subclasses from services; the
  HTTP layer maps them to problem details. New error classes get a stable
  `problem_type`.
* **Identifiers.** Never expose sequential ids. Use `normalize_identifier`
  on input; use counters for generation. See `docs/architecture/identifiers.md`.
* **Immutability.** Any write to a revision or its BOM lines calls
  `assert_editable` first. Anything physical must reference a frozen
  revision.
* **Migrations** are hand-reviewed. Autogenerate is a starting point, not
  the end. Name constraints through the metadata naming convention.
* **Enumerations** are `StrEnum`s stored as strings with check constraints.
* **No relationship access at import time across modules.** A module-level
  `selectinload(Model.relationship)` configures every mapper SQLAlchemy has seen
  so far; if another module's model is still importing, configuration fails with
  "failed to locate a name". Keep loader options inside functions when a module
  imports models from a module that imports it back, and import cross-module
  models lazily where needed (see `suppliers/service.py`).
* **Quantities** are `Decimal` / `NUMERIC`, never floats.
* **Tests** exercise the service layer directly for rules, and the HTTP
  layer for contract shape. Factories build data through services.

## Frontend

* **Types come from the API.** Import from `@nemeth/domain-types`; never
  hand-declare an API shape.
* **Queries live in `lib/queries.ts`** with centralised keys; pages compose
  hooks and render.
* **No invented domain logic.** Allowed lifecycle transitions, resolution
  rules and validation come from the API. The UI shows what the API says.
* **Empty states are honest.** Missing data is shown as missing. Planned
  areas say which slice they belong to and show nothing fake.
* **Identifiers are monospace.** Engineering numbers are tabular. Decimal
  strings from the API are trimmed for display, never rounded.
* **Strict TypeScript** with `noUncheckedIndexedAccess`; ESLint
  type-checked rules; Prettier with the Tailwind plugin.

## Naming

* Python: `snake_case`, modules singular by concept (`components`, `bom`).
* TypeScript: `PascalCase` components, `camelCase` hooks (`useComponent`),
  one feature folder per navigation area.
* Database: `snake_case` tables in plural (`component_revisions`),
  constraint names from the naming convention.
* Human identifiers: uppercase with hyphens (`N1-MVT-002`), documented in
  `docs/architecture/identifiers.md`.

## Commit-sized increments

Prefer several small, reviewable commits per slice: schema + migration;
service + tests; API; UI; docs. Every commit should leave `pytest` and
`npm run build` green.
