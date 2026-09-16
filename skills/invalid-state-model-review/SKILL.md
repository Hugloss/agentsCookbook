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

Enumerate representable combinations versus real valid combinations. Trace defensive branches, cleanup, or repeated validation caused by impossible states being constructible.

## DO NOT REPORT

Do not report optional fields whose independence is real. Do not introduce a state-machine framework merely to replace one enum.

## PREFER

Use stronger concrete/discriminated types or tighter schemas when they remove invalid combinations and downstream branches.

## OUTPUT

Return `# Invalid State Model Review` with model, impossible combinations, production consequences, defensive code caused, target representation, removals, and tests/invariants.
