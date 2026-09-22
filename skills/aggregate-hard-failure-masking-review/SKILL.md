---
name: aggregate-hard-failure-masking-review
description: Finds aggregate scores or averages that allow hard contract violations to be compensated by unrelated positive measurements.
license: MIT
---

# Aggregate Hard-Failure Masking Review

Standalone, read-only qualification aggregation review.

## INVARIANT

> **A hard contract violation cannot be averaged, weighted, or scored away by unrelated successes.**

## HUNT

Hunt for:
- weighted sums combining safety/authority failures with quality gains;
- average pass thresholds that tolerate forbidden states;
- percentage-success gates that hide one critical failure;
- ranking/economics improvements compensating correctness violations;
- aggregate dashboards used as qualification authority without hard vetoes.

## PROVE

Build one input containing a hard violation plus enough positive soft metrics to cross the aggregate pass threshold. Trace the code that returns qualified/pass despite the forbidden state.

## DO NOT REPORT

Do not report ordinary trade-off scoring where every metric is explicitly soft and no hard invariant is claimed.

## PREFER

Evaluate hard vetoes first, readiness second, then lower-order quality/economics metrics. Keep non-compensatory failures explicit in the result.

## OUTPUT

Return `# Aggregate Hard-Failure Masking Review` with hard invariant, aggregate path, compensating metrics, false pass, corrected gate order, verification.
