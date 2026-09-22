---
name: authority-escalation-review
description: Finds candidates, heuristics, diagnostics, scores, or inferred evidence that gain authority without an explicit qualifying proof.
license: MIT
---

# Authority Escalation Review

Standalone, read-only authority-flow review.

## INVARIANT

> **Derived evidence must not leave a layer with greater authority than it entered unless that layer contributes explicit qualifying proof.**

## HUNT

Hunt for transitions such as:
- candidate → owner;
- ranked → proven;
- inferred → authoritative;
- diagnostic → qualification;
- observed → complete;
- external hint → repository or execution authority;
- high score → safe/actionable;
- structural correlation → permission.

## PROVE

Name the evidence state on entry, the stronger state exposed on exit, and the exact proof added by the transforming layer. A finding exists when authority increases but no new admissible proof closes the gap.

## DO NOT REPORT

Do not report a validator or adjudicator that really adds the evidence required by the stronger contract and records that proof explicitly.

## PREFER

Represent candidate, ambiguity, admissibility, proof scope, completeness, and authority separately. Make authority transitions explicit and one-way.

## OUTPUT

Return `# Authority Escalation Review` with findings: input authority, transformation, output authority, missing proof, real consequence, canonical authority boundary, verification.
