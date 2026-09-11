# ADR-006: BOM lines belong to an assembly revision and reference a child component with an optional pin

**Status:** Accepted
**Date:** 2026-09-11

## Context

The BOM must be recursive (assemblies of assemblies), must be part of the
revisioned engineering definition (a Case Assembly Rev B has a defined
content), and must support exact traceability of what is inside a physical
watch. Two classic designs exist:

1. **Fully pinned.** Each line references an exact child revision. Precise,
   but every child change forces a cascade of parent revisions. Heavy for
   a one-person shop iterating daily.
2. **Floating.** Each line references a child component; the revision is
   whatever is current. Light, but "what is in this design" changes
   silently as children evolve.

A separate concern is the difference between the *design* BOM (intent)
and the *as-built* configuration (fact).

## Decision

* There is no standalone "BOM" entity. The BOM of an assembly is the set
  of `BomLine` rows owned by one of its `ComponentRevision`s. This makes
  BOM content part of the immutable revision (ADR-004).
* A `BomLine` references a **child component** and, optionally, a
  **pinned child revision**. Unpinned lines resolve at query time to the
  child's latest revision (development) or latest released revision
  (production), chosen by a `resolve` parameter. The resolver reports, per
  node, whether the revision came from a pin or from the mode.
* The **as-built** configuration of a physical prototype or watch is
  recorded separately (slice 10) as `PartInstance`s that always reference
  exact, frozen revisions. Design BOM = what should be inside. Build
  record = what is inside.
* Invariants: only `ASSEMBLY` components own lines; no cycles at any
  depth; `find_number` unique per parent; no edits to lines of frozen
  parents; a pin must belong to the child component.
* Where-used is a query over `BomLine` by child component (and by child
  revision for pinned lines).

## Consequences

* Development stays light: iterate a wheel through Revs A–D without
  touching the gear train assembly's revision.
* When it matters, pin. A released assembly should pin every line; a
  future validation rule can enforce "released assemblies are fully
  pinned".
* Exact traceability of physical units does not depend on pinning at all,
  because build records carry exact revisions.
