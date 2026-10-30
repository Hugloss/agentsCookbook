---
name: test-orchestration-complexity-review
description: Finds tests that must coordinate too many subsystems, states, mocks, callbacks, or lifecycle steps to prove one behavior.
license: MIT
---

# Test Orchestration Complexity Review

Standalone, read-only test-complexity-as-architecture-feedback review.

## INVARIANT

> **If proving one behavior requires orchestrating half the system, inspect the production architecture.**

## HUNT

Hunt tests with excessive fixtures, deep mocks, callback choreography, many lifecycle states, complex cleanup, broad dependency bags, branching, or many unrelated assertions.

## PROVE

Trace which production responsibilities force the test to understand those concepts. Separate scenario complexity from architecture-induced complexity. Establish an unnecessary responsibility/dependency and a concrete failure or maintenance consequence before reporting a defect; fixture, mock, callback, or line counts alone are leads. Show how the proposed boundary reduces required concepts while preserving the same behavioral assertion.

## DO NOT REPORT

Do not report a complex end-to-end test whose workflow is genuinely complex. Never hide orchestration in a test helper and call the problem solved.

## PREFER

Reduce production responsibilities, states, or dependencies so the test naturally becomes smaller. Keep real behavior intact.

## OUTPUT

Return `# Test Orchestration Complexity Review` with the inspected scenario, orchestration map, proved unnecessary responsibility, consequence, target boundary, and equivalent simpler test. Separate leads from `FINDING`. A bounded `CLEAN`/`LEAVE ALONE` needs the scenario's coordination duties traced and justified; use `INSUFFICIENT EVIDENCE` when the production obligation is missing rather than prescribing a rewrite from test size.
