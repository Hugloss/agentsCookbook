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

Identify the exact claimed improvement and the evidence it requires. Inspect comparable pre/post observations and establish whether the metric is unchanged, worse, redistributed, or unsupported by any claimed measurement. A code trace can prove removal of a duplicated traversal or owner; it cannot by itself prove a percentage latency, throughput, memory, or fleet-cost improvement. Distinguish an unsubstantiated claim from an observed failed improvement. If measurement evidence is merely unavailable to the reviewer, do not infer that no measurement occurred; preserve that question as unknown.

## DO NOT REPORT

Do not report behavior-preserving refactors that make no measurable improvement claim, or a precise structural simplification proved directly by source evidence. Do not require timing runs before implementing an evident optimization; measurement is required to support the corresponding measured claim, not to authorize the code change.

## PREFER

Separate correctness qualification, source-proved structural changes, and measured optimization/debt claims. Require comparable observations appropriate to the actual claim; reuse sufficient existing evidence and refuse to manufacture measured progress from structural movement alone.

## OUTPUT

Return `# Improvement Claim Remeasurement Review` with claimed improvement, pre/post evidence, comparability, actual result, false claim path, and verification.

Use `FINDING` for an unsupported or contradicted measurable claim, stating which it is. `CLEAN` covers only the inspected claims and comparable evidence; unclear claim scope or unavailable evidence is `INSUFFICIENT EVIDENCE`, never an invented regression or improvement.
