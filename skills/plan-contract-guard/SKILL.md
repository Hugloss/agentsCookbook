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

Establish the user's requested end state, governing requirements and handoff boundary before assessing the deliverable. Show why each missing item prevents safe execution or objective completion. Blocking open questions, unresolved severe findings, and unverifiable completion fail the contract. Separate a proved omission or contradiction from evidence that could not be inspected. Do not infer repository-wide readiness from a complete-looking document.

## DO NOT REPORT

Do not fail a handoff for cosmetic structure or optional detail. A requirement may be satisfied by a verified reference to an existing owner; no duplicate section, rollback procedure for an effect-free change, or new validation gate is required merely to fill the checklist.

## PREFER

Make decisions explicit, keep scope tight, and turn vague quality claims into observable completion criteria.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, compare the completed implementation evidence against the user request and claimed end state. Check scope completion, validation, recovery where relevant, unresolved ambiguity, and whether the handoff can truthfully claim completion.

Return `# Build Contract Review` with verdict, inspected obligations, blocking findings, non-blocking findings, missing validation/evidence, concrete fixes, and remaining risk. Use `None` only when each material obligation in the declared boundary is accounted for by inspected evidence. Missing required evidence is `INSUFFICIENT EVIDENCE`, not complete.

## OUTPUT

Otherwise return `# Plan Contract Report` with verdict, inspected obligations, required-contract check, scope/intent check, decision completeness, validation/recovery check, leakage check, and concrete fixes. Apply the same obligation accounting as build review. Preserve proved contract failures even if other obligations remain unresolved; a complete plan is not an executed implementation.
