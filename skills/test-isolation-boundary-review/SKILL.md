---
name: test-isolation-boundary-review
description: Finds pure or local behavior that cannot be tested without unrelated filesystem, database, network, process, or framework effects.
license: MIT
---

# Test Isolation Boundary Review

Standalone, read-only testability/production-boundary review.

## INVARIANT

> **Pure behavior should not require unrelated effects to exist.**

## HUNT

Hunt unit-like tests that require databases, filesystem trees, servers, subprocesses, framework mounting, full application startup, or giant mock trees. Trace which production API forces those effects into the behavior.

## PROVE

Establish the behavior's input/output contract and show that it does not semantically require the external effect. Trace the production dependency that forces the effect, then identify the natural existing boundary where decision/computation and effect can be separated. Preserve tests of actual effect integration; an effect mocked away is not evidence that integration still works.

## DO NOT REPORT

Do not label real integration behavior as an isolation failure. Do not create one-implementation interfaces purely for mocking.

## PREFER

Expose pure decision/computation through an existing domain/application boundary and leave integration tests where integration matters.

## OUTPUT

Return `# Test Isolation Boundary Review` with inspected behavior/dependencies, forced effects, proved coupling cause, natural isolation boundary, removable setup, and simpler test shape. Use `FINDING` for a demonstrated unrelated dependency; reserve `CLEAN`/`LEAVE ALONE` for traced dependency paths whose effects are absent or required. An unknown behavioral contract or dependency owner requires `INSUFFICIENT EVIDENCE`, not an invented pure boundary.
