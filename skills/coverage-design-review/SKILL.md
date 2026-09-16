---
name: coverage-design-review
description: Checks whether tests prove real production behavior and plausible failures instead of merely executing code.
license: MIT
---

# Coverage Design Review

Standalone, read-only behavioral coverage review. Coverage percentage is not the target.

## INVARIANT

> **Tests should prove real behavior and plausible failure modes, not merely execute lines.**

## HUNT

Start from real production entry paths and observable outcomes. Hunt for missing coverage of:
- input variation and invalid input;
- repeated operations and state changes;
- partial failure, retry, interruption, and recovery;
- lifecycle and cross-component behavior;
- tests that mock away the behavior they claim to verify.

## PROVE

For each material gap name a plausible broken implementation that would still pass today. Tie the gap to a real production path and observable outcome.

## DO NOT REPORT

Do not report line coverage alone, artificial edge cases with no production path, or implementation coupling unless it creates false confidence. `test-contract-coupling-review` owns tests that freeze private choreography.

## PREFER

Use the smallest test level that proves the behavior: isolated logic, component/integration boundary, then a few critical workflow tests. Keep meaningful behavior real rather than replacing it with mocks.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, inspect the changed production paths and the tests/validation supplied for them. Find realistic behavior or failure modes the implementation could get wrong while all supplied tests still pass.

Return `# Build Coverage Review` with blocking findings, non-blocking findings, missing behavioral coverage, concrete tests/fixes, and remaining risk. Use `None` when coverage is sufficient.

## OUTPUT

Otherwise return `# Coverage Design Review` with verdict, real-usage model, meaningful gaps, mocking/artificial-path risks, missing outcome assertions, and recommended test portfolio. For each gap: problem, real-world risk, current weakness, better test, priority.
