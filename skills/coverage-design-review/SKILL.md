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

First identify the applicable behavior obligations and the production paths and tests actually inspected. For each material gap name a plausible broken implementation that would still pass today. Trace why the existing assertions, including coverage delegated to another test level, would miss it. Tie the gap to a real production path and observable outcome. A hypothetical broken implementation proves a coverage weakness only when that missed detection is established; it does not prove that production currently has the defect.

## DO NOT REPORT

Do not report line coverage alone, artificial edge cases with no production path, or implementation coupling unless it creates false confidence. Do not demand duplicate integration tests when a smaller existing check proves the same obligation. Tests outside the supplied patch may supply coverage; unavailable tests leave that question unresolved. `test-contract-coupling-review` owns tests that freeze private choreography.

## PREFER

Use the smallest test level that proves the behavior: isolated logic, component/integration boundary, then a few critical workflow tests. Keep meaningful behavior real rather than replacing it with mocks.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, inspect the changed production paths and the tests/validation supplied for them. Find realistic behavior or failure modes the implementation could get wrong while all supplied tests still pass.

Return `# Build Coverage Review` with inspected obligations and tests, blocking findings, non-blocking findings, missing behavioral coverage, concrete tests/fixes, and remaining risk. Use `None` only when each material obligation in that scope has a decisive inspected check; use `INSUFFICIENT EVIDENCE` for obligations whose tests or behavior contracts are unavailable.

## OUTPUT

Otherwise return `# Coverage Design Review` with verdict, inspected obligations and tests, real-usage model, meaningful gaps, mocking/artificial-path risks, missing outcome assertions, and recommended test portfolio. For each gap: problem, real-world risk, current weakness, better test, priority. Separate proved detection gaps from uninspected coverage; neither a passing suite nor a partial test inventory supports a repository-wide coverage claim.
