---
name: invalid-state-model-review
description: Finds data models that can represent lifecycle or domain combinations the real system says are impossible.
license: MIT
---

# Invalid State Model Review

Standalone, read-only type/state-model review.

## INVARIANT

> **The model should not represent combinations the real system says are impossible.**

## HUNT

Inspect important lifecycle, operation, admission, result, configuration, identity, and persistence models. Hunt for:
- status plus unrelated booleans;
- enums plus nullable evidence;
- stringly typed states;
- fields valid only in certain phases;
- duplicated status indicators;
- contradictory timestamps or identities.

## PROVE

Derive forbidden combinations from the current domain/lifecycle contract, not field names or a preferred type style. Trace construction, deserialization, mutation and admission into trusted consumers. Show a forbidden combination that can cross that boundary, or concrete avoidable downstream complexity caused by repeatedly handling it. Distinguish language-level representability from states the canonical validator actually admits.

## DO NOT REPORT

Do not report optional fields whose independence is real, raw transport/input models intentionally validated once before trusted use, or transient states permitted inside an enforced atomic boundary. Trust-boundary revalidation is not inherently redundant. Do not introduce a state-machine framework merely to replace one enum.

## PREFER

Use stronger concrete/discriminated types or tighter schemas when they remove invalid combinations and downstream branches.

## OUTPUT

Return `# Invalid State Model Review` with the governing invariant, model/admission boundary, forbidden and legitimate control states, reachable consequence or avoidable downstream cost, smallest representation correction, and verification.

Use `FINDING` for a demonstrated admitted invalid state or material model-induced complexity; `CLEAN` only when the declared construction/admission/mutation scope is complete and its admitted states satisfy the invariant; `LEAVE ALONE` when one proved boundary rejects invalid inputs or permits the suspected state intentionally; otherwise `INSUFFICIENT EVIDENCE`. Do not infer all model states are safe from a few happy-path examples.
