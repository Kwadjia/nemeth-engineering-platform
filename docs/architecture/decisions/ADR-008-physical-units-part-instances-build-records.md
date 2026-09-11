# ADR-008: Physical genealogy — part instances and build records shared by prototypes and watches

**Status:** Accepted
**Date:** 2026-09-11

## Context

The design BOM (ADR-006) says what *should* be inside an assembly. Traceability
questions such as "what exact revision of every component is inside N1-017?"
and "what watches contain this revision?" need facts about *physical* parts
and the events that put them into a unit. Prototypes (N1-P001) and serialized
watches (N1-001) are different concepts to the watchmaker, but the genealogy
underneath them is the same.

## Decision

* A **PartInstance** is one physical part. It always references an exact
  **frozen** `ComponentRevision` (ADR-004): a part cannot exist against a
  definition that may still change. It carries serial/lot, source
  (`IN_HOUSE`, `PURCHASED`, `SALVAGED`, `OTHER`), material and heat-treatment
  lots, supplier note, a status (`AVAILABLE`, `INSTALLED`, `REMOVED`,
  `SCRAPPED`) and a denormalised `current_prototype_id` for fast "where is it
  now" queries.
* A **BuildRecord** is an append-only assembly event on one unit: date,
  who, title, procedure text (lubrication, torque, sequence), notes, and an
  ordered list of **BuildEntry** rows, each `INSTALL` or `REMOVE` of one part
  instance at an optional position. Records are never edited except for
  their free-text notes; corrections are new records.
* The **current configuration** of a unit is derived: every part instance
  whose latest entry on that unit is an `INSTALL`. It is never stored as a
  separate list.
* `BuildRecord` links to the unit through explicit nullable foreign keys,
  `prototype_id` now and `watch_id` in slice 10, with a check constraint
  that exactly one is set. Two clear tables, one shared event structure, no
  polymorphic generic keys.
* Part instances can move between units over time (salvaged from a
  prototype into another); the entries preserve that history.

## Consequences

* "What is inside N1-P001 right now" and "what was inside it on a given
  date" are both answerable from build entries alone.
* Physical where-used ("which prototypes contain Rev B of the escape
  wheel") is a join from revision → part instance → current prototype.
* Recording a build forces revisions to be frozen first. This is
  deliberate: the moment a part exists, its definition is history.
* Watches (slice 10) add a table and one column; no genealogy code changes.
