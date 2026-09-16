---
name: coverage-design-review
description: Checks whether tests follow real production usage and would catch plausible broken behavior.
license: MIT
---

# Coverage Design Review

Standalone, read-only coverage-design review. Evaluate behavioral confidence rather than coverage percentage.

Do not assume a coordinator, Ping-Pong, prior validation gate, run store, or sibling reviewer. The subject may be a plan, existing tests, implementation evidence, or a direct coverage question.

## Method

- Establish the normal production entry path and observable behavior relevant to the subject.
- Identify realistic failures: input variation, invalid input, repeated operations, state changes, partial failure, retries, interruption, recovery, lifecycle, and cross-component interaction where applicable.
- Compare those behaviors with proposed/existing tests.
- Flag tests that only execute lines, only prove no exception occurred, use artificial call paths, mock away the behavior under review, or omit meaningful outcome assertions.
- Prefer the simplest suitable level: isolated unit tests, realistic component tests, and a few workflow tests for critical paths.
- For each important test ask what plausible broken implementation could still pass.
- In `BUILD REVIEW MODE`, tie findings to changed files, diff/test evidence, or skipped checks.
- Never edit files, run commands, invoke agents, or provide patches.

## Output

Normal mode: `# Coverage Design Review` with Coverage Design Verdict (`Strong`, `Needs Improvement`, or `Insufficient Evidence`); Real Usage Model; Meaningful Coverage Gaps; Mocking And Artificial-Path Risks; Missing Outcome Assertions; Recommended Test Portfolio; Repo Facts Used.

For each meaningful gap include Problem, Real-world risk, Current test weakness, Better test, and Priority (`HIGH`, `MEDIUM`, `LOW`).

Build mode: `# Build Review Report` with Blocking Findings; Non-Blocking Findings; Missing Validation; Suggested Fixes; Evidence Inspected; Confidence / Remaining Risk.

Use `None` rather than manufacturing findings.
