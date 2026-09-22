---
name: correlation-causation-boundary-review
description: Finds shared target, temporal, dependency, or structural correlation promoted into causation, incident identity, responsibility, or remediation authority.
license: MIT
---

# Correlation Causation Boundary Review

Standalone, read-only inference-boundary review.

## INVARIANT

> **Correlation identifies correspondence; it does not establish causation, incident identity, responsibility, or what should change without separate evidence.**

## HUNT

Hunt for:
- two observations resolving to the same repository target and becoming one incident;
- dependency/version change treated as cause of a failure automatically;
- temporal proximity promoted into causal attribution;
- structural ownership interpreted as runtime causation;
- correlation output selecting remediation/edit targets without consumer reasoning;
- shared module/path evidence becoming responsibility proof.

## PROVE

Trace the correlation fact and the stronger downstream conclusion. Show the missing causal/adjudication evidence required for that transition.

## DO NOT REPORT

Do not report explicitly labeled correspondence that remains non-causal and is passed to a separate consumer/adjudicator.

## PREFER

Keep correspondence facts explicit, label causation as not-inferred until proven, and separate repository observation from diagnosis/remediation authority.

## OUTPUT

Return `# Correlation Causation Boundary Review` with correlation fact, stronger inferred claim, missing causal evidence, authority consequence, corrected boundary, and verification.
