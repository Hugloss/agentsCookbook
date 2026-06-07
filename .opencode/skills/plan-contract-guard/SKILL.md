---
name: plan-contract-guard
description: Final plan contract checklist. Use when checking required plan sections, coordinator ownership, no transcript or ledger leakage, scope alignment, decision completeness, validation, rollback, and remaining open questions.
license: MIT
---

# Plan Contract Guard

Behavioral guidelines for checking whether a final plan is ready to hand to an implementer.

**Tradeoff:** This skill biases toward contract compliance over narrative polish. Do not reject a plan for formatting preference if the plan is complete and safe.

## 1. Check Required Sections

A final implementation plan should include:
- Goal.
- Assumptions.
- Ordered steps.
- Files or areas to inspect.
- Risks and edge cases.
- Validation with acceptance criteria.
- Rollback or recovery.
- Remaining open questions.

Missing or empty required sections are contract issues.

## 2. Preserve Master Ownership

The final plan must be one coordinator-authored artifact.

Flag:
- Pasted subagent reports.
- Raw transcripts.
- Decision ledgers.
- Adopted/rejected/deferred tables exposed as internal process.
- Text that makes a reviewer the final plan owner.

## 3. Enforce Decision Completeness

The implementer should not need to choose unresolved basics.

Flag vague instructions:
- "Update relevant files."
- "Adjust config as needed."
- "Handle edge cases."
- "Add tests."

Accept them only when paired with concrete targets, behavior, and validation.

## 4. Check Scope And Intent

Required work must match the user request.

Separate:
- Required changes needed for the request.
- Optional improvements.
- Out-of-scope ideas to ignore or defer.

## 5. Require Verifiable Completion

Validation and rollback must be concrete enough to execute.

Fail the contract when:
- Acceptance criteria are not binary.
- Blocking open questions remain.
- Rollback is absent for config or install-path changes.
- Severe validation, risk, simulation, or fact findings are ignored without a repo-fact or user-scope reason.
