---
name: improvement-claim-remeasurement-review
description: Finds refactor, cleanup, performance, or debt-reduction claims inferred from code movement instead of fresh comparable post-change measurement.
license: MIT
---

# Improvement Claim Remeasurement Review

Standalone, read-only post-change improvement review.

## INVARIANT

> **Behavior preservation can qualify a change, but an improvement claim requires fresh comparable evidence that the intended metric actually improved.**

## HUNT

Hunt for claims that:
- helper extraction reduced complexity without remeasurement;
- file splitting reduced debt by moving findings;
- caching improved performance without post-change timing/work evidence;
- fewer lines imply better locality or ownership;
- refactor completion is treated as debt reduction automatically;
- before/after metrics use incomparable definitions or scopes.

## PROVE

Find the claimed improvement metric, reproduce or inspect a comparable pre/post measurement, and show the metric is unchanged, worse, redistributed, or unmeasured despite the positive claim.

## DO NOT REPORT

Do not report behavior-preserving refactors that make no measurable improvement claim.

## PREFER

Separate correctness qualification from optimization/debt claims. Require explicit pre/post comparable receipts and refuse to manufacture progress from structural movement alone.

## OUTPUT

Return `# Improvement Claim Remeasurement Review` with claimed improvement, pre/post evidence, comparability, actual result, false claim path, and verification.
