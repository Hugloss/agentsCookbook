---
name: orthogonal-state-axis-review
description: Finds one status, enum, or flag that collapses independent semantic dimensions such as freshness, authority, completeness, validity, or lifecycle.
license: MIT
---

# Orthogonal State Axis Review

Standalone, read-only state-model review.

## INVARIANT

> **Independent semantic dimensions must remain independently representable and must not be inferred from one another without an explicit invariant.**

## HUNT

Hunt for statuses such as:
- safe-fresh / safe-stale / unsafe;
- ready / stale / invalid mixtures;
- one field encoding candidate selection plus ownership;
- health values that combine freshness and integrity;
- completeness inferred from validity;
- lifecycle state inferred from authority;
- serializers that collapse several axes and cannot represent legal combinations.

## PROVE

Identify at least two independent dimensions and one legal combination the current model cannot express correctly, or one branch that infers axis B from axis A without proof.

## DO NOT REPORT

Do not report a composite state machine or exhaustive tagged encoding merely because it uses one field. Leave it alone when every legal combination and relevant distinction is representable and consumers preserve them, whether the axes are coupled by domain law or encoded as an explicit product.

## PREFER

Model orthogonal axes separately, derive presentation summaries afterward, and keep authority-bearing decisions on the primitive dimensions.

## OUTPUT

Return `# Orthogonal State Axis Review` with collapsed dimensions, unrepresentable or misclassified state, consequence, separated model, and verification.

Use `FINDING` for a proved legal state that is lost or misclassified. `CLEAN` covers the inspected domain states and consuming branches; uncertain independence or uninspected serialization paths remain `INSUFFICIENT EVIDENCE`. Do not infer failure from enum shape alone.
