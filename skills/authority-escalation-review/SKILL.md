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

Establish the governing contract for the stronger claim independently of the implementation being reviewed. Name the evidence state on entry, the stronger state accepted on exit, its reachable consumer, and the exact qualifying proof added by the transforming layer. Show why the available evidence cannot justify that transition and what decision it changes. An unavailable upstream proof is an evidence gap, not proof that none exists.

## DO NOT REPORT

Do not report a validator or adjudicator that establishes the stronger contract from admissible existing evidence; a new observation is not always necessary. Preserve explicit policy-authorized decisions under uncertainty when they do not misrepresent that uncertainty as a proven fact.

## PREFER

Represent candidate, ambiguity, admissibility, proof scope, completeness, and authority separately. Make authority transitions explicit and one-way.

## OUTPUT

Return `# Authority Escalation Review` with the inspected authority chain, governing contract, input authority, transformation, accepted output authority, missing proof, consequence, correction and verification. Distinguish proved findings from inaccessible proof obligations.

End with `FINDING` for a proved unjustified authority increase; `CLEAN` only when every transition and material consumer in the declared chain was traced and each authority increase is justified; `LEAVE ALONE` for a positively justified adjudication; or `INSUFFICIENT EVIDENCE` when the contract or admissible proof cannot be established. Bound every absence claim to the inspected chain.
