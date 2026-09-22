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

Trace both measurement receipts and name the differing dimension. Show how the comparison code still computes a delta, improvement, regression, or ranking without rejecting or normalizing that difference.

## DO NOT REPORT

Do not report deliberate cross-environment studies that include an explicit calibration/normalization model and do not present raw deltas as directly comparable.

## PREFER

Bind a comparability identity to the measurement contract and fail closed on mismatches before computing deltas.

## OUTPUT

Return `# Measurement Comparability Review` with compared measurements, mismatched dimensions, invalid conclusion, required comparability contract, verification.
