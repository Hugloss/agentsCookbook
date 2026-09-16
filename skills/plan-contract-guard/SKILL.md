---
name: plan-contract-guard
description: Checks whether a handoff is scoped, executable, verifiable, recoverable, and free of material ambiguity.
license: MIT
---

# Plan Contract Guard

Standalone, read-only final handoff review.

## INVARIANT

> **A handoff must function as an executable contract, not a collection of intentions.**

## HUNT

Hunt for missing or weak:
- goal and scope;
- assumptions;
- ordered implementation steps or completed-change evidence;
- concrete files/areas;
- ownership;
- risks and edge cases;
- validation and acceptance criteria;
- rollback/recovery;
- material open questions.
Also hunt for workflow transcripts, scratch ledgers, or reviewer bookkeeping leaked into the deliverable.

## PROVE

Show why each missing item prevents safe execution or objective completion. Blocking open questions, unresolved severe findings, and unverifiable completion fail the contract.

## DO NOT REPORT

Do not fail a handoff for cosmetic structure or optional detail.

## PREFER

Make decisions explicit, keep scope tight, and turn vague quality claims into observable completion criteria.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, compare the completed implementation evidence against the user request and claimed end state. Check scope completion, validation, recovery where relevant, unresolved ambiguity, and whether the handoff can truthfully claim completion.

Return `# Build Contract Review` with verdict, blocking findings, non-blocking findings, missing validation/evidence, concrete fixes, and remaining risk. Use `None` when the implementation contract is complete.

## OUTPUT

Otherwise return `# Plan Contract Report` with verdict, required-contract check, scope/intent check, decision completeness, validation/recovery check, leakage check, and concrete fixes.
