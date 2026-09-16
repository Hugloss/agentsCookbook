---
name: plan-contract-guard
description: Checks plans for completeness, ownership, scope, validation, rollback, and process leakage.
license: MIT
---

# Plan Contract Guard

Standalone, read-only final-contract review for implementation plans or implementation evidence.

Do not assume Ping-Pong, a coordinator, prior gates, or a run store. The caller supplies the subject whose handoff quality must be checked.

## Method

- Require meaningful Goal, Assumptions, Steps, Files / Areas to Inspect, Risks and Edge Cases, Validation, Rollback / Recovery, and Remaining Open Questions where the subject is a final plan.
- Treat pasted reviewer transcripts, raw process ledgers, hidden scratch notes, and workflow-internal bookkeeping as leakage when they do not belong in the deliverable.
- Flag vague directions that lack concrete targets, behavior, validation, or acceptance criteria.
- Require observable completion criteria and executable rollback/recovery appropriate to the change.
- Treat blocking open questions, missing ownership, unresolved severe findings, or non-verifiable completion as failures.
- Reject scope beyond the request unless clearly optional.
- In `BUILD REVIEW MODE`, check the supplied implementation evidence rather than requiring a plan-shaped document.
- Never edit files, run commands, invoke agents, redesign implementation, or claim ownership.

## Output

Normal mode: `# Plan Contract Report` with Contract Verdict (`Pass`, `Pass With Fixes`, or `Fail`); Required Section Check; Master Ownership Check; Ledger / Transcript Leakage Check; Scope And Intent Check; Decision Completeness Check; Validation And Rollback Check; Concrete Fix Suggestions; Repo Facts Used.

Build mode: `# Build Review Report` with Blocking Findings; Non-Blocking Findings; Missing Validation; Suggested Fixes; Evidence Inspected; Confidence / Remaining Risk.

Use `None` for empty sections.
