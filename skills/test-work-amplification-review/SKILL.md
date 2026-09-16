---
name: test-work-amplification-review
description: Finds tests whose small behavioral assertion triggers disproportionate production work and traces the architectural cause.
license: MIT
---

# Test Work Amplification Review

Standalone, read-only measured test-performance review.

## INVARIANT

> **A test should pay only for the behavior it proves.**

## HUNT

Measure slow tests and trace them into production. Hunt for repository-wide scans, filesystem/subprocess work, full bootstrap, repeated parsing, excessive database setup, broad validation, unrelated integration work, and repeated production operations.

## PROVE

Show `test → behavior → production path → expensive work`, measured timing where available, and why the work is unnecessary for the behavior. Separate test overhead from production cost.

## DO NOT REPORT

Do not report a legitimately expensive integration test when the cost is exactly what it exists to verify. Do not make tests faster by mocking away meaningful behavior.

## PREFER

Remove unnecessary production work first. Keep assertions and behavioral fidelity. Remeasure after the structural change.

## OUTPUT

Return `# Test Work Amplification Review` with measured slow tests, production paths, root causes, architecture fixes, expected cost shape, and before/after measurement plan.
