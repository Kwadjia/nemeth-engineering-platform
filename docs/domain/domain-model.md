# Domain Model

This document defines the vocabulary of the NEMETH Engineering Platform and
how the concepts relate. It is the reference for the database schema, the
API and the UI. Where a concept is not yet implemented, the section is
marked **(planned)** with the slice in which it arrives.

Read this alongside [`identifiers.md`](../architecture/identifiers.md) and
the ADRs in [`docs/architecture/decisions/`](../architecture/decisions/).

## Traceability questions

The schema exists to answer these questions, now or later. Each maps to a
path through the model.

| Question | Path through the model |
|---|---|
| What exact revision of every component is inside N1-017? | Prototype/`Watch` → `BuildRecord` entries → installed `PartInstance` → `ComponentRevision` *(prototypes done; watches slice 10)*; design intent via `ProductModel` → root assembly → resolved BOM tree *(done)* |
| Who manufactured the escape wheel? | `PartInstance.source` + `supplier_note` *(done)*; `Supplier` / `ManufacturingOrder` *(slice 12)*; design-level default via `ComponentRevision.supplier_note` |
| What material and heat treatment was used? | `ComponentRevision.material`, `.heat_treatment`, `.finish` *(done)*; actual `material_lot` / `heat_treatment_lot` on `PartInstance` *(done)* |
| What CAD file generated the part? | `ComponentRevision` → `Attachment(kind=CAD)` with SHA-256 *(slice 11)* |
| What inspection measurements were recorded? | `PartInstance` → `TestRun(type=DIMENSIONAL_INSPECTION)` → `Measurement` *(slice 9)* |
| What experiments caused us to change from Rev B to Rev C? | `EngineeringChange.evidence` → `Experiment`; `EngineeringChange.affected_revision`, `.proposed_revision` *(slices 8, 12)* |
| What was the timing performance before and after? | `Experiment` → `TestRun` (before/after) → `Measurement` *(slices 8, 9)* |
| What watches contain this revision? | `ComponentRevision` ← `PartInstance.current_prototype` *(prototypes done; watches slice 10)*; design-level via where-used *(done)* |
| What parts failed inspection? | `TestRun.outcome = FAIL` → `Nonconformance` *(slices 9, 12)* |
| What torque / lubrication / assembly procedure was used? | `AssemblyStep` on a `BuildRecord` → `WorkInstruction` revision *(slice 10+)* |

## Concept map

```
Product ──< ProductModel >── Caliber
              │                 │
              │ root assembly   │ root assembly
              ▼                 ▼
          Component (kind = ASSEMBLY | PART, family, identifier)
              │
              └──< ComponentRevision (A, B, C … ; lifecycle state; engineering content)
                        │
                        └──< BomLine ──▶ child Component [+ pinned ComponentRevision]

Prototype (planned) ──< BuildRecord (planned) ──< PartInstance ──▶ ComponentRevision
Watch (serialized, planned) ──< BuildRecord

Experiment (planned) ──< TestRun ──< Measurement
EngineeringChange (planned) ──▶ affected/proposed ComponentRevision, evidence Experiment
Attachment (planned) ──▶ any entity (polymorphic link), stored via FileStorage
Supplier (planned) ◀── ComponentRevision.supplier, PartInstance.supplier
```

## Product definition (implemented)

### Product
A marketable product line. Example: **NEMETH N1**.

| Field | Notes |
|---|---|
| `identifier` | Short code, e.g. `N1`. Unique. |
| `name` | `NEMETH N1` |
| `description` | |
| `lifecycle_state` | See [Lifecycle states](#lifecycle-states) |
| `notes` | Free text |
| audit | `created_at/by`, `updated_at/by` |

### ProductModel (reference)
A specific configuration of a Product, e.g. **N1.01**. In horology this is
the *reference*. A model chooses a caliber and a top-level watch assembly.

| Field | Notes |
|---|---|
| `product_id` | Owning product |
| `identifier` | `N1.01`. Unique. |
| `name`, `description`, `notes` | |
| `lifecycle_state` | |
| `caliber_id` | Optional until chosen |
| `root_component_id` | The top-level watch assembly component whose BOM defines the model |

### Caliber
A mechanical movement treated as a first-class engineered product.
Example: **Caliber N1** (`CAL-N1`).

| Field | Notes |
|---|---|
| `identifier` | `CAL-N1` |
| `name`, `description`, `notes` | |
| `lifecycle_state` | |
| `root_component_id` | The movement assembly component whose BOM is the caliber's BOM |
| `architecture` | Free text: "manual wind, single barrel, Swiss lever" |
| `diameter_mm`, `thickness_mm` | Numeric |
| `frequency_bph` | Beats per hour (18 000 / 21 600 / 28 800 …) |
| `jewel_count` | |
| `power_reserve_hours` | |
| `lift_angle_deg` | Needed to compute amplitude from a timegrapher |
| `target_amplitude_deg` | |
| `target_rate_tolerance_spd` | ± seconds/day |
| `specification` | JSONB for evolving fields: barrel configuration, gear ratios, tooth/pinion counts, balance inertia, hairspring properties, escapement geometry. Promote a key to a typed column when it is queried or validated. |

## Components and revisions (implemented)

### Component
The **identity** of an engineered item: what it is, independent of how it is
currently designed. A component never changes meaning; its design changes
through revisions.

| Field | Notes |
|---|---|
| `identifier` | `N1-MVT-002`. Unique. Generated per family or supplied. |
| `name` | `Mainplate` |
| `kind` | `PART` or `ASSEMBLY`. Only assemblies may have BOM lines. |
| `family` | Subsystem grouping used for identifiers and filtering: `WATCH`, `CASE`, `DIAL`, `HAND`, `MVT`, `STRAP`, `PKG`, `MISC` |
| `description` | |
| `is_placeholder` | True for seed/sample data. Shown prominently in the UI. |
| audit | |

Derived: `latest_revision` (highest revision number), `released_revision`
(highest revision number in state `RELEASED`).

### ComponentRevision
The **engineering content** of a component at a point in time. Revisions are
lettered `A, B, … Z, AA, AB …` and numbered `1, 2, 3 …` for ordering.

| Field | Notes |
|---|---|
| `component_id` | |
| `revision_number`, `revision_label` | `3`, `C` |
| `lifecycle_state` | State machine below |
| `change_summary` | Why this revision exists ("Increase clearance between third wheel and bridge") |
| `description` | Revision-specific description |
| `material` | `316L stainless`, `CuBe2`, `brass CuZn39Pb3` |
| `heat_treatment` | |
| `finish` | `Rhodium plated`, `Geneva stripes`, `sandblast` |
| `manufacturing_method` | `CNC milling`, `wire EDM`, `external supplier` … (free text now; process routing arrives with manufacturing) |
| `dimensions` | JSONB: `{ "diameter_mm": 25.6, "thickness_mm": 1.2 }` — keys per component type |
| `tolerances` | JSONB: `{ "diameter_mm": "±0.01" }` |
| `mass_g` | If applicable |
| `supplier_note` | Free text until `Supplier` exists (slice 12), when `supplier_id` is added |
| `inspection_requirements` | Text; becomes structured with inspection plans later |
| `notes` | |
| `frozen_at` | Timestamp at which the revision became immutable |
| `superseded_by_id` | Set when a later revision is created from this one |
| audit | |

**Immutability rule (ADR-004).** A revision is editable while in `CONCEPT`
or `DESIGN`. On transition to `PROTOTYPE` (or any later state) it is
*frozen*: its engineering content and its BOM lines can no longer be
modified, and it can never be deleted. Any further change requires a new
revision, which copies the content of the source revision as a starting
point. The rule is: **once a physical part could have been made from a
revision, that revision is history.**

### Lifecycle states

Shared by products, models, calibers and component revisions.

```
CONCEPT ──▶ DESIGN ──▶ PROTOTYPE ──▶ VALIDATION ──▶ RELEASED ──▶ OBSOLETE
   │           │           │             │
   └───────────┴───────────┴─────────────┴──────────────────────▶ OBSOLETE
```

* Forward transitions only, with one exception: `DESIGN → CONCEPT` is
  allowed (a design can be sent back to the drawing board) because nothing
  physical depends on either state.
* `OBSOLETE` is reachable from any state and is terminal.
* Revisions become **frozen** on entering `PROTOTYPE`, `VALIDATION`,
  `RELEASED` or `OBSOLETE`.

## Bill of materials (implemented)

### BomLine
A line on the **design BOM** of an assembly revision.

| Field | Notes |
|---|---|
| `parent_revision_id` | The assembly revision that owns the line |
| `child_component_id` | What goes in |
| `child_revision_id` | Optional **pin** to an exact child revision. When null the child resolves to its latest (or released) revision at query time. |
| `find_number` | Position on the drawing / balloon number (10, 20, 30 …). Unique per parent revision. |
| `quantity` | Numeric; `unit` defaults to `ea` |
| `reference_designator` | Optional: "screw at 11 o'clock" |
| `notes` | |

Invariants enforced in the service layer and tested:

* Only `ASSEMBLY` components own BOM lines.
* A component cannot contain itself, directly or through any depth.
* Lines cannot be added, edited or removed on a frozen parent revision.
* `find_number` is unique within a parent revision.
* A pinned child revision must belong to the child component.

**Resolution.** A BOM tree is resolved from a root revision with a mode:
`latest` (default during development) or `released` (for production). A
pinned line always resolves to its pin. The response records, per node,
which rule produced the revision, so the UI can show pins explicitly. A
child with no revision satisfying the mode is reported as `unresolved`
rather than silently dropped.

**Design BOM vs. as-built.** The design BOM describes intent. The as-built
configuration of a physical prototype or watch is recorded separately as
`PartInstance`s on a `BuildRecord` (slice 10) and always references exact
revisions. That is where "what exact revision is inside N1-017" is answered
definitively; the design BOM answers "what should be inside an N1.01".

## Physical genealogy (implemented, ADR-008)

### Prototype
A physical development build. `N1-P001`. Fields: identifier, name, purpose,
status (`PLANNED` → `BUILDING` → `ACTIVE` → `RETIRED`, forward only), product
model and/or caliber under test, started/retired dates, notes. Recording the
first build with entries moves a planned prototype to `BUILDING`.

### PartInstance
One physical part. `PI-00042`. Always references an exact **frozen**
`ComponentRevision`; recording a part against an editable revision is
rejected. Fields: serial number, lot, source (`IN_HOUSE`, `PURCHASED`,
`SALVAGED`, `OTHER`), material lot, heat-treatment lot, supplier note,
status (`AVAILABLE`, `INSTALLED`, `REMOVED`, `SCRAPPED`), and
`current_prototype_id` (where it is now). A `quantity` on creation records
several identical parts as separate instances.

### BuildRecord and BuildEntry
An append-only assembly event on a prototype. `BR-00007`: title, performed
on/by, procedure (steps, lubrication, torque, sequence as performed), notes,
and ordered entries, each `INSTALL` or `REMOVE` of one part instance at an
optional position. Rules: a part cannot be installed while it is installed
elsewhere; it can only be removed from the unit it is in; the same part
appears at most once per record; retired prototypes accept no records; only
a record's notes can be edited afterwards.

**Configuration is derived**, never stored: the parts whose latest entry on
the unit is an `INSTALL`, each with its exact revision, position and the
record that installed it. Physical where-used answers "which prototypes
contain a part made to this revision".

Serialized watches (slice 10) add `Watch` and a `watch_id` on `BuildRecord`
with a check that exactly one unit is set; the genealogy code is shared.

## Experiments (implemented)

### Experiment
Iterative development treated like software. `EXP-014`. A lab-notebook
record with sections: objective, hypothesis, configuration, methodology,
equipment, procedure, observations, results, conclusion, follow-up, notes.
Status `PLANNED` → `IN_PROGRESS` → `COMPLETED`, or `ABANDONED` from either
open state; `outcome` (`IMPROVEMENT`, `NO_CHANGE`, `REGRESSION`,
`INCONCLUSIVE`) is recorded when known. Dates: started, completed.

Links (many-to-many, each with a free-text role such as *subject*,
*control*, *before*, *after*): `ExperimentPrototype` and
`ExperimentRevision`. These are the evidence trail that engineering
changes (slice 12) cite: "what experiments caused Rev B → Rev C" is
`ExperimentRevision` rows for both revisions. Test runs and measurements
attach to an experiment in slice 9; attachments in slice 11.

## Development (planned)

### TestType, TestRun and Measurement (implemented)
An **extensible measurement model**:

* `TestType` — a registry row: code (`TIMEGRAPHER`, `POWER_RESERVE`,
  `WATER_RESISTANCE`, `DIMENSIONAL_INSPECTION`, `TORQUE`, `TEMPERATURE`,
  `MAGNETISM`, `VISUAL_INSPECTION`, `CUSTOM`, plus any you add), name, a
  **metric list** (`key`, `label`, `unit`), whether custom metric keys are
  allowed, and whether readings are taken per position. New test types are
  rows, not migrations; built-ins are installed by the seed and never
  overwritten.
* `TestRun` (`TR-00042`) — a session: test type, at most one subject
  (prototype, part instance, or component revision; watches join in slice
  10), optional experiment, performed at/by, equipment, `conditions` JSON
  (temperature, humidity, state of wind), outcome (`PASS`/`FAIL`/`INFO`),
  notes.
* `Measurement` — **one observation per row** (long format): `metric`,
  `value` (NUMERIC), `unit` (defaulted from the type's metric list),
  `position` (`DU`, `DD`, `CU`, `CD`, `CL`, `CR` for position-based types),
  `recorded_at`, notes, `extra` JSON. Validated against the type: unknown
  metrics are rejected unless the type allows custom keys. A timegrapher
  reading in one position is three rows sharing a position; a later reading
  for the same metric and position supersedes the earlier one in summaries
  while both remain stored.

The long format keeps analytics in SQL: rate over time for a prototype,
amplitude before and after an experiment, per-position deltas. The
**timing summary** (per-position rate/amplitude/beat error, mean rate,
delta, amplitude range, max beat error, lift angle) is derived on read for
any timegrapher run and exposed for a prototype's latest run and on the
dashboard.

### Watch (implemented)
A serialized unit: `N1-001` (serial `001`, derived from the identifier),
product model, status (`PLANNED` → `IN_BUILD` → `BUILT`, then
`PERSONAL_PROTOTYPE` / `DELIVERED` / `IN_SERVICE` move freely; `RETIRED`
terminal), owner, origin prototype, assembled and delivered dates, notes.

Watches share the genealogy structure with prototypes (ADR-008):
`BuildRecord.watch_id`, `PartInstance.current_watch_id` and
`TestRun.watch_id`, each guarded by a check constraint so a record has
exactly one unit, a part has one location and a run one subject. Moving a
part from a prototype into a watch is a removal record on one and an
install record on the other; both stay in the history.

The **dossier** (`GET /watches/{ref}/dossier`) is the digital build record
in one document: product, model, caliber, origin prototype, current
configuration with exact revisions, the build log, test runs with the
latest timing summary, and the experiments linked to the origin prototype.
Service history, issues and modifications are later additions to it.

## Manufacturing and quality (planned)

`Supplier`, `ManufacturingProcess`, `ProcessRoute` (ordered steps such as
*CNC rough → CNC finish → deburr → surface grind → jewel-hole inspection →
anglage → Geneva stripes → rhodium plate → final inspection*),
`WorkInstruction` (revisioned), `Material`, `ToolMachine`,
`Nonconformance`, `Issue`. See
[`docs/manufacturing/README.md`](../manufacturing/README.md).

## Documents (planned, slice 11)

`Attachment` — polymorphic link `(entity_type, entity_id)` plus file
metadata: original filename, stored key, SHA-256, MIME type, size,
uploaded at/by, kind (`CAD`, `DRAWING`, `PHOTO`, `TEST_RESULT`,
`CERTIFICATE`, `OTHER`), description. Bytes live in `FileStorage`
(ADR-003), never in PostgreSQL.

## Engineering change (planned, slice 12)

`EngineeringChange` — `ECR-0021`: title, reason, affected component
revision(s), proposed revision(s), evidence (experiments, test runs),
status (`DRAFT`, `PROPOSED`, `APPROVED`, `IMPLEMENTED`, `REJECTED`),
approvals. Lightweight at first; the concept and the links are what matter.

## Audit and identity

Every important record carries `created_at`, `created_by`, `updated_at`,
`updated_by`. The actor comes from the auth boundary (`Actor`), which today
returns a configured local user. Full audit logging (row-level history) is
a later addition; the primitives are in place.

Internal identity is a UUID. Human identifiers are separate, unique and
never reused. See [`identifiers.md`](../architecture/identifiers.md).
