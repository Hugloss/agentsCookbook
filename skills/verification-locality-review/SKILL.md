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

Identify the edit/behavior target, the selected verifier, and a stronger available verifier. Compare direct/indirect references, namespace/task locality, and behavioral ownership. Show how the weaker verifier can miss the changed behavior or lengthen validation.

## DO NOT REPORT

Do not report a broader verifier merely because a narrower test exists when the broader verifier has stronger direct behavioral ownership or reference evidence.

## PREFER

Keep reference evidence authoritative, then use target namespace/task locality as a bounded discriminator when reference strength does not decide.

## OUTPUT

Return `# Verification Locality Review` with target, selected verifier, stronger candidate, evidence comparison, consequence, selection correction, and verification.
