---
name: evidence-readiness-review
description: Finds qualification or success claims made before the evidence set is proven eligible, non-vacuous, and sufficient for required semantic slices.
license: MIT
---

# Evidence Readiness Review

Standalone, read-only qualification readiness review.

## INVARIANT

> **A positive qualification result is valid only after the evidence set is proven eligible, non-vacuous, and sufficient for the scope required by its governing qualification contract.**

## HUNT

Hunt for:
- empty datasets passing because there are zero violations;
- all-skipped or all-filtered suites reported as success;
- shadow, canary, diagnostic, or historical rows becoming the only score-bearing evidence;
- required task/risk/semantic slices missing while aggregate quality passes;
- the candidate narrowing the qualification scope or required population after observing evidence;
- unresolved ground truth included as if adjudicated;
- readiness checked after scoring instead of before it.

## PROVE

Establish the governing qualification contract and the evidence scope/slices it requires independently of candidate success. Then construct or identify an evidence set that lacks a required eligibility or coverage condition but still reaches pass/qualified. Identify the missing readiness predicate and the downstream claim it invalidates.

## DO NOT REPORT

Do not report optional sparse diagnostics that make no qualification, certification, or completeness claim. Do not require evidence outside the governing qualification scope merely because more data could exist.

## PREFER

Gate scoring on authority-derived readiness: valid membership, non-empty eligible evidence, required slices, adjudicated truth, and explicit scope. Treat unknown governing scope as incomplete rather than letting the candidate choose a smaller scope that already passes.

## OUTPUT

Return `# Evidence Readiness Review` with governing qualification contract, required scope/slices, claimed qualification, observed evidence membership, missing prerequisite, vacuous/invalid pass path, corrected gate, verification.
