---
name: measurement-comparability-review
description: Finds before/after or cross-run comparisons made across incompatible scope, population, configuration, tool, environment, or execution mode.
license: MIT
---

# Measurement Comparability Review

Standalone, read-only measurement integrity review.

## INVARIANT

> **A delta or comparison is meaningful only when every dimension required for comparability is equal or explicitly normalized.**

## HUNT

Hunt for comparisons across changed:
- source universe or selected population;
- filters, thresholds, policy, or configuration;
- tool/schema versions;
- environment or execution mode;
- sampling strategy or denominator;
- task/corpus membership;
- measurement command or metric definition.

## PROVE

Name the comparison claim and intended changed variable, then trace both measurement receipts. Identify a differing dimension that confounds that claim rather than constituting its intended treatment. Show how the comparison still emits an unsupported delta, improvement, regression, or ranking without a justified design or normalization. Equal metadata alone does not establish a suitable population, sampling design, or uncertainty for the claim.

## DO NOT REPORT

Do not report a changed implementation, tool, or environment merely because it is the declared subject of a controlled comparison. Leave alone appropriately designed cross-environment studies with justified calibration/normalization or an explicitly limited descriptive claim; do not infer causal improvement from an uncontrolled raw delta.

## PREFER

Record the intended treatment and bind a comparability identity to the fixed measurement contract. Reject or qualify confounding mismatches before interpreting deltas; do not reject the declared treatment merely because it changed.

## OUTPUT

Return `# Measurement Comparability Review` with compared measurements, mismatched dimensions, invalid conclusion, required comparability contract, verification.

Use `FINDING` for a material confound presented as a valid comparison. Bound `CLEAN` to the inspected claims, populations, and measurement contracts; unknown confounding dimensions or unsupported normalization leave `INSUFFICIENT EVIDENCE`.
