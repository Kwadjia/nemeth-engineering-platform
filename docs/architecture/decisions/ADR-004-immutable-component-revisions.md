# ADR-004: Immutable component revisions with a frozen threshold

**Status:** Accepted
**Date:** 2026-09-11

## Context

"Never overwrite historical engineering information" is a first principle.
At the same time, a one-person shop iterates quickly: a material typo on a
freshly created revision should not require a new revision letter. We need
a rule that is strict where it matters and forgiving where nothing depends
on the record yet.

## Decision

A `ComponentRevision` has a lifecycle state:

```
CONCEPT → DESIGN → PROTOTYPE → VALIDATION → RELEASED → OBSOLETE
```

* While in `CONCEPT` or `DESIGN`, the revision's engineering content and
  BOM lines are **editable**.
* On entering `PROTOTYPE` or any later state the revision is **frozen**:
  `frozen_at` is set, and every write to its content or its BOM lines is
  rejected with `409 Conflict`. Frozen revisions are never deleted. No
  delete endpoint exists for revisions at all.
* The threshold is `PROTOTYPE` because that is the first state in which a
  physical part may have been made from the definition. **Once a part
  could exist, the definition is history.**
* Transitions are forward-only, with two exceptions: `DESIGN → CONCEPT`
  (nothing physical depends on either) and `* → OBSOLETE`.
* A new revision is created from a source revision (default: the latest).
  Content is copied, the letter increments, the source's `superseded_by_id`
  is set, and the new revision starts in `CONCEPT`. `change_summary`
  records why.
* `Component` itself holds only identity (identifier, name, kind, family,
  description). Renaming a component is allowed and does not create a
  revision; the identifier is immutable.

## Consequences

* History is preserved exactly where it can be depended on.
* A prototype built from Rev B and a later Rev C can be compared field by
  field forever.
* Engineering changes (slice 12) reference frozen revisions safely.
* Anything physical (part instances, build records) must reference a
  frozen revision; the service layer will enforce this when those arrive.
