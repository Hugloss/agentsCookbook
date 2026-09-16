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

Run or reason about different ordering/isolation where practical. Identify the exact shared production state, its lifetime, writers, and why tests must clean it.

## DO NOT REPORT

Do not report intentional immutable shared resources. Do not solve contamination only by adding a larger global reset fixture.

## PREFER

Give mutable state an explicit owner and lifetime, or move it to the operation/test instance that actually owns it.

## OUTPUT

Return `# Test State Contamination Review` with shared state, contamination path, reproducing order, ownership defect, target lifetime, reset code that can disappear, and proof.
