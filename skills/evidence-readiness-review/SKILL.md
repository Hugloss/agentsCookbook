---
name: evidence-readiness-review
description: Finds qualification or success claims made before the evidence set is proven eligible, non-vacuous, and sufficient for required semantic slices.
license: MIT
---

# Evidence Readiness Review

Standalone, read-only qualification readiness review.

## INVARIANT

> **A positive qualification result is valid only after the evidence set is proven eligible, non-vacuous, and sufficient for the claimed scope.**

## HUNT

Hunt for:
- empty datasets passing because there are zero violations;
- all-skipped or all-filtered suites reported as success;
- shadow, canary, diagnostic, or historical rows becoming the only score-bearing evidence;
- required task/risk/semantic slices missing while aggregate quality passes;
- unresolved ground truth included as if adjudicated;
- readiness checked after scoring instead of before it.

## PROVE

Construct an evidence set that lacks a required eligibility or coverage condition but still reaches pass/qualified. Identify the missing readiness predicate and the downstream claim it invalidates.

## DO NOT REPORT

Do not report optional sparse diagnostics that make no qualification, certification, or completeness claim.

## PREFER

Gate scoring on explicit readiness: valid membership, non-empty eligible evidence, required slices, adjudicated truth, and declared scope.

## OUTPUT

Return `# Evidence Readiness Review` with claimed qualification, readiness requirements, missing prerequisite, vacuous/invalid pass path, corrected gate, verification.
