---
name: semantic-noninterference-review
description: Finds conclusions that change when only inputs outside the declared semantic dependency or proof scope are modified.
license: MIT
---

# Semantic Non-Interference Review

Standalone, read-only metamorphic dependency review.

## INVARIANT

> **A semantic conclusion changes only when admitted evidence within its declared dependency or proof scope changes.**

## HUNT

Hunt for conclusions affected by:
- irrelevant repository additions;
- unrelated documents, tests, or metadata;
- equivalent task wording;
- presentation-only changes;
- external evidence outside the authority boundary;
- iteration order or incidental neighboring candidates.

Also verify the converse: removing or changing decisive admitted evidence must be able to change the conclusion.

## PROVE

Establish the semantic dependency contract from the supported request and actual decision inputs; do not let a candidate label a relevant dependency out of scope. Construct or trace a counterfactual pair that changes only irrelevant evidence and compare semantic output. Use a control whose independently established correct answer changes to exclude a frozen implementation. Removing redundant support need not change the answer while another valid proof remains.

## DO NOT REPORT

Do not report a result change when the modified input is explicitly part of the declared semantic dependency or proof scope.

## PREFER

Declare semantic dependencies, isolate proof inputs from ambient context, and add paired irrelevant-change/decisive-change metamorphic tests.

## OUTPUT

Return `# Semantic Non-Interference Review` with conclusion, declared scope, irrelevant mutation, observed interference, decisive control mutation, correction, verification.

Use `FINDING` for proved influence from semantically irrelevant input. `CLEAN` is limited to the inspected dependency contract and mutation classes; an unestablished scope or inconclusive control is `INSUFFICIENT EVIDENCE`. Do not label an unexecuted counterfactual as an observed result.
