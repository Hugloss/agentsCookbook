---
name: semantic-redecision-review
description: Finds repeated semantic decisions inside one authority chain when no competing accepted authority or backward resolved-fact boundary is proved.
license: MIT
---

# Semantic Redecision Review

Standalone, read-only review of **unnecessary repeated interpretation**.

## INVARIANT

> **One semantic question is decided once within its authority chain; consumers reuse that meaning instead of independently answering it again.**

## HUNT

Trace callers, services, workers, helpers, diagnostics, and adapters for repeated decisions about eligibility, readiness, status, policy, capability, identity, or classification. Look for matching conditionals, decision tables, and independently derived booleans fed from the same inputs.

## PROVE

1. Name the *identical semantic question*, scope, and declared first decision owner.
2. Trace two reachable interpretations within one authority chain; show why both answer the same question rather than separate domain questions.
3. Show where the later interpretation affects a real branch, outcome, warning, or diagnostic, or duplicates owner work and can drift.
4. Verify the later answer is **not** independently accepted as authoritative (otherwise use `single-source-of-truth-review`).
5. Verify this is **not** a consumer discarding an already available resolved result to rederive it from raw inputs across a resolved boundary (use `resolved-fact-regression-review`).
6. Specify the single result to transport, repeated code to delete, and a focused behavioral regression.
7. Record inspected paths and gaps; `CLEAN` requires complete inspection of the declared question's in-scope decision paths.

## DO NOT REPORT

Do not treat repeated syntax as identical semantics. Preserve trust-boundary integrity checks, distinct phase/domain decisions, read-only projections, and legitimate verification of a resolved result. An unsupported suspicion is not a finding.

### Routing boundary

`single-source-of-truth-review` owns **competing accepted authority**; `resolved-fact-regression-review` owns **backtracking from an available resolved result to raw inputs**; `canonical-consumer-contract-review` owns **a consumer obligation broken by an allowed refinement of its owner's result**, even if that consumer contains redundant parsing.

If one defect triggers multiple symptoms, report the earliest proven causal owner as primary; reference related symptoms without requesting duplicate repairs.

## PREFER

Reuse the first authoritative answer. Delete later classifiers, redundant branches, and reconstruction helpers without adding a new facade, adapter, validator, or execution path.

## OUTPUT

Return `# Semantic Redecision Review` with semantic question/scope, first owner, repeated interpretation, real consumer consequence, canonical result, removable code, focused regression, and inspected/uninspected paths.

End with exactly one:
- `FINDING` — one question is independently reanswered within an authority chain with a reachable consequence;
- `CLEAN` — the declared in-scope decision paths were traced without repeated interpretation;
- `LEAVE ALONE` — similar-looking code performs distinct decisions or integrity verification;
- `INSUFFICIENT EVIDENCE` — semantic equivalence or a reachable second decision cannot be established.
