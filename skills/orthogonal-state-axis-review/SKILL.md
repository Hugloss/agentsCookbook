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

Do not report a composite state machine when the dimensions are truly coupled by domain law and every legal state is representable.

## PREFER

Model orthogonal axes separately, derive presentation summaries afterward, and keep authority-bearing decisions on the primitive dimensions.

## OUTPUT

Return `# Orthogonal State Axis Review` with collapsed dimensions, unrepresentable or misclassified state, consequence, separated model, and verification.
