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

Trace the actual correlation fact into an accepted causal, responsibility or remediation conclusion. Establish the stronger claim's evidence requirement and show the precise unsupported inference and its reachable consequence. Search the relevant adjudication path before asserting that proof is absent; inaccessible causal evidence remains unknown.

## DO NOT REPORT

Do not report explicitly labeled correspondence passed to a separate adjudicator, an investigative lead, or a policy-defined grouping key that does not claim causation. A legitimate incident-grouping contract may use correlation; prove that a stronger unsupported claim is actually made.

## PREFER

Keep correspondence facts explicit, label causation as not-inferred until proven, and separate repository observation from diagnosis/remediation authority.

## OUTPUT

Return `# Correlation Causation Boundary Review` with inspected correlation/adjudication paths, the stronger claim, required and available evidence, consequence, corrected boundary and a causal/non-causal control.

Use `FINDING` for a proved unsupported promotion; `CLEAN` only after the declared inference and consumer paths were traced with no unsupported promotion or unresolved material proof; `LEAVE ALONE` for explicitly non-causal correspondence or independently justified attribution; otherwise `INSUFFICIENT EVIDENCE`. Scope the conclusion to the inspected inference boundary.
