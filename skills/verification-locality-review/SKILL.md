---
name: verification-locality-review
description: Finds verification evidence selected by generic rank while stronger target-bound, namespace-local, or reference-backed verification is available.
license: MIT
---

# Verification Locality Review

Standalone, read-only verification-selection review.

## INVARIANT

> **Verification should prefer the strongest evidence bound to the behavior being changed, not merely the highest generic retrieval rank.**

## HUNT

Hunt for:
- unrelated canonical tests displacing direct reference-backed tests;
- generic repository-tooling tests selected over target namespace/module tests;
- verification chosen before exact edit ownership is known;
- changed behavior with stronger direct/indirect reference evidence ignored;
- fallback ranking that treats all zero-reference candidates as equally useful despite clear task locality.

## PROVE

Identify the edit/behavior target, the selected verifier, and a stronger available verifier. Inspect their actual assertions, reachable production paths, discovery conditions, and applicable environment; filename proximity or a call reference alone does not establish behavioral strength. Show a changed-behavior failure the selected verifier can miss, or concrete unrelated work it introduces, while preserving required broader coverage.

## DO NOT REPORT

Do not report a broader verifier merely because a narrower test exists when the broader verifier has stronger direct behavioral ownership or reference evidence.

## PREFER

Keep reference evidence authoritative, then use target namespace/task locality as a bounded discriminator when reference strength does not decide.

## OUTPUT

Return `# Verification Locality Review` with inspected target/selection scope, selected verifier, stronger candidate, behavioral evidence comparison, consequence, correction, and verification. Use `FINDING` only when the candidate is demonstrably stronger for that obligation. `CLEAN`/`LEAVE ALONE` requires the relevant candidates and selection rule to be inspected; unavailable assertions or execution conditions remain `INSUFFICIENT EVIDENCE`. A local test choice does not certify whole-suite coverage.
