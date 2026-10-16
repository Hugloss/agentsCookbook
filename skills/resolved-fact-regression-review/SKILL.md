---
name: resolved-fact-regression-review
description: Finds consumers crossing backward from an available authoritative resolved fact to raw inputs to resolve that same fact again.
license: MIT
---

# Resolved Fact Regression Review

Standalone, read-only review of **backward semantic data flow**.

## INVARIANT

> **After a canonical fact is resolved, downstream code must consume or validate that fact—not abandon it and reinterpret its raw inputs for the same meaning.**

## HUNT

Trace `RAW → VALIDATED → RESOLVED → CONSUMER/EFFECT`. Look for execution, persistence, recovery, or reporting consumers that receive an already resolved identity, configuration, policy, binding, capability, or status but instead infer the same answer again from names, flags, paths, payload fields, or storage columns.

## PROVE

1. Name the fact, scope, canonical resolver, and the *available* resolved result.
2. Trace a reachable boundary where the result could be consumed but is dropped, ignored, replaced, or bypassed.
3. Trace raw/unresolved inputs into the consumer's independent resolution of the **same fact**.
4. Show a material drift, mismatch, bypass, or redundant decision; identify the raw fallback and the smallest API/flow correction.
5. Specify a focused regression proving the consumer uses the resolved result, including a case where raw and canonical meanings differ.
6. Record inspected paths and unknowns; `CLEAN` requires all declared in-scope resolved-to-consumer paths to be traced.

## DO NOT REPORT

Do not flag:
- legitimate use of raw inputs for a **different** downstream obligation;
- a trust-boundary assertion or integrity revalidation that cannot change the already resolved meaning;
- repeated policy decisions before any resolved-result boundary was crossed.

### Routing boundary

- `single-source-of-truth-review`: two independent results can be accepted as authority for the same fact.
- `semantic-redecision-review`: repeated interpretation without abandoning an available resolved result across the boundary.
- `canonical-consumer-contract-review`: one consumer's obligation breaks when its authoritative owner's result is legitimately refined, without independent re-resolution from raw inputs.

When the same trace shows overlapping symptoms, identify one primary defect and refer to the others without separate duplicate repairs.

## PREFER

Pass the resolved semantic result, not the raw ingredients needed to recreate it. Remove fallback resolution and redundant parser/decision code. Retain independently required raw inputs only for their distinct purposes.

## OUTPUT

Return `# Resolved Fact Regression Review` with fact/scope, authoritative result, backward boundary, raw re-resolution path, consequence, correction/deletions, focused regression, and inspected/uninspected scope.

End with exactly one:
- `FINDING` — a reachable consumer bypasses an available resolved result and re-resolves the same fact from raw inputs;
- `CLEAN` — every declared in-scope consumer uses the resolved result without backward resolution;
- `LEAVE ALONE` — raw inputs serve a distinct obligation or only verify a resolved fact;
- `INSUFFICIENT EVIDENCE` — the available resolved result or backward trace cannot be established.
