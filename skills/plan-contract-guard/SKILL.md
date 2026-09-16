---
name: plan-contract-guard
description: Checks whether a final plan is scoped, executable, verifiable, recoverable, and free of unresolved handoff ambiguity.
license: MIT
---

# Plan Contract Guard

Standalone, read-only final handoff review.

## INVARIANT

> **A final plan must function as an executable contract, not a collection of intentions.**

## HUNT

Hunt for missing or weak:
- goal and scope;
- assumptions;
- ordered implementation steps;
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

Do not fail a plan for cosmetic structure or optional detail. In BUILD REVIEW MODE, apply the same contract to supplied change/evidence rather than forcing plan sections.

## PREFER

Make decisions explicit, keep scope tight, and turn vague quality claims into observable completion criteria.

## OUTPUT

Return `# Plan Contract Report` with verdict, required-contract check, scope/intent check, decision completeness, validation/recovery check, leakage check, and concrete fixes.
