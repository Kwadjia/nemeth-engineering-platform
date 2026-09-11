# Manufacturing

This area is **not implemented in v0.1**. It documents how manufacturing
concepts will attach to the platform so the current schema is built with
them in mind.

## Concepts

* **ManufacturingProcess** — a catalogue of process types: CNC milling,
  CNC turning, manual watchmaker lathe, wire EDM, laser cutting, grinding,
  gear cutting, polishing, hand finishing, electroplating, heat treatment,
  external supplier.
* **ProcessRoute** — an ordered list of steps for making one
  `ComponentRevision`. Routes are revisioned with the component revision
  they belong to. Example for *Mainplate Rev C*:

  1. CNC rough machining
  2. CNC finish machining
  3. Deburr
  4. Surface grind
  5. Jewel-hole inspection
  6. Hand anglage
  7. Geneva stripes
  8. Rhodium plate
  9. Final inspection

* **WorkInstruction** — a revisioned document attached to a route step or
  an assembly step: text, parameters (torque, lubricant, quantity),
  photos, drawings.
* **ManufacturingOrder / Operation** — a run of a route for N parts; each
  operation records who, when, which machine, and outcome.
* **Traveler** — the operation history of one `PartInstance`; derived, not
  stored separately.
* **Material**, **ToolMachine** — catalogues referenced by routes and
  operations.
* **Nonconformance** — a failed inspection or deviation, linked to the
  part instance, the test run and (optionally) an engineering change.

## What v0.1 already provides

* `ComponentRevision.manufacturing_method` (free text) and
  `inspection_requirements` — the seed for routes and inspection plans.
* Immutable revisions, so a route can safely reference the exact
  definition it manufactures.
* `storage/manufacturing/` for CAM programs, setup sheets and travelers
  once attachments exist.

Do not build an MES until parts are being made in volume. Build routes
and travelers when the first batch of in-house parts is machined.
