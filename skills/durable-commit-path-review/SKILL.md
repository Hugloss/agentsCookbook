---
name: durable-commit-path-review
description: Finds durable state transitions that can be decided or committed through more than one semantic path.
license: MIT
---

# Durable Commit Path Review

Standalone, read-only state-transition review.

## INVARIANT

> **One durable transition should have one semantic transition authority and one canonical commit path.**

## HUNT

Inventory important transitions: create, admit, place, start, complete, fail, cancel, publish, retire, recover, acknowledge, promote, restore. Hunt every way each can commit through API, worker, retry, recovery, admin, cleanup, scheduler, or migration.

## PROVE

Separate `DECISION` (when transition becomes valid) from `COMMIT` (where durable state changes). Show duplicate commit paths, partial ordering, retry ambiguity, or stale decision risk on real production flows.

## DO NOT REPORT

Multiple callers are not duplicate authorities when they converge cleanly on one transition. Do not demand a generic transaction framework.

## PREFER

Many callers → one explicit transition → one atomic/idempotent commit where required. Preserve exact expected identity/revision and terminal evidence.

## OUTPUT

Return `# Durable Commit Path Review` with transition map and problematic transitions: decision, commit, duplicate paths, atomicity/ordering risk, target path, removal, deterministic proof.
