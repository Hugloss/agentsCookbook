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

Show that the behavior itself does not semantically require the external effect, then identify the natural existing boundary where decision/computation and effect can be separated.

## DO NOT REPORT

Do not label real integration behavior as an isolation failure. Do not create one-implementation interfaces purely for mocking.

## PREFER

Expose pure decision/computation through an existing domain/application boundary and leave integration tests where integration matters.

## OUTPUT

Return `# Test Isolation Boundary Review` with behavior, forced effects, production coupling cause, natural isolation boundary, code/setup removable, and simpler test shape.
