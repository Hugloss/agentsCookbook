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

Name the transition, entity identity and expected generation. Separate `DECISION` (when transition becomes valid) from `COMMIT` (where durable state changes). Trace each accepted writer and the guard that authorizes its commit. Prove that independent paths can establish the same transition with inconsistent eligibility, ordering, retry or stale-generation behavior; show the reachable consequence. Multiple SQL statements or call sites alone do not prove multiple semantic authorities.

## DO NOT REPORT

Multiple callers are not duplicate authorities when they converge on one enforced transition contract. Preserve recovery paths that replay that contract and different transitions or generations with different owners. A single database constraint/CAS may enforce authority across several callers. Do not demand a generic transaction framework.

## PREFER

Many callers → one explicit transition → one atomic/idempotent commit where required. Preserve exact expected identity/revision and terminal evidence.

## OUTPUT

Return `# Durable Commit Path Review` with transition scope, traced decision/commit map, accepted writers, conflicting guards, consequence, target owner and a decisive regression/control. Name writer paths that could not be inspected.

Use `FINDING` for a proved competing transition authority; `CLEAN` only after all writers in the declared transition scope were traced and share one enforced transition contract; `LEAVE ALONE` when callers demonstrably share one enforced contract; otherwise `INSUFFICIENT EVIDENCE`. A single path exposing a partial outcome belongs to `atomic-operation-review`.
