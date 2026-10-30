---
name: test-state-contamination-review
description: Finds tests that depend on hidden mutable state, global caches, singletons, environment, or leftovers from other tests.
license: MIT
---

# Test State Contamination Review

Standalone, read-only test isolation/state-lifetime review.

## INVARIANT

> **One test should not depend on invisible state left by another.**

## HUNT

Hunt for global reset fixtures, singleton replacement, cache clearing, module reloads, environment restoration, process isolation, order-sensitive failures, and tests that pass alone but fail in the suite.

## PROVE

Run or reason about different ordering/isolation where practical. Identify the exact shared state in production or test support, its lifetime, writers, and reset owner. Show `test A writes → state survives → test B observes a different result than its declared baseline`, including worker/run namespaces when relevant. A global reset fixture is not itself a defect if it reliably restores owned mutable state before each consumer.

## DO NOT REPORT

Do not report intentional immutable shared resources. Do not solve contamination only by adding a larger global reset fixture.

## PREFER

Give mutable state an explicit owner and lifetime, or move it to the operation/test instance that actually owns it.

## OUTPUT

Return `# Test State Contamination Review` with the inspected tests/state/reset scope, contamination sequence, ownership defect, target lifetime, removable resets, and proof. Label reasoned sequences separately from executed ordering checks. Use `FINDING` for established cross-test influence; `CLEAN`/`LEAVE ALONE` requires a traced isolation or reset boundary. Unknown writers/reset behavior requires `INSUFFICIENT EVIDENCE`, not an assumption that every shared fixture contaminates tests.
