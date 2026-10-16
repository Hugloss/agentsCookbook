---
name: single-source-of-truth-review
description: Proves when two reachable paths can independently establish authoritative truth for the same fact, scope, and generation.
license: MIT
---

# Single Source of Truth Review

Standalone, read-only review of **split semantic authority**.

## INVARIANT

> **For one semantic fact in one scope and generation, one owner establishes authoritative truth. Other paths may transport, verify, cache, or project its result, but must not independently establish an alternative accepted truth.**

## HUNT

Trace real production, tests, build, packaging, admission, recovery, and execution paths. Look for:
- multiple producers/default providers of one accepted manifest, identity, policy, configuration, readiness, prerequisite, or execution authority;
- caller-, entrypoint-, phase-, environment-, or outer-workflow-dependent choice of the authority for the *same* fact;
- independent bootstrap/normalizer/build/package compensators all claiming to supply one prerequisite;
- two nominally equivalent owners accepted by the same consumer or certification path.

Repeated interpretation is **not** enough. This skill requires at least two paths that can **establish or override accepted authority**.

## PROVE

1. Name the fact, exact scope/generation, and contract that makes a result authoritative.
2. Trace at least two real reachable paths, including what accepts their results as truth.
3. Classify each touchpoint: **owner**, **transport**, **verification**, **cache**, **projection**, **consumer**, or **compensating producer**.
4. Show that two independent producers/selections can establish authoritative results for the same fact, even if current values happen to agree.
5. Establish the path/context selecting each owner and a material consequence (drift, missing prerequisite, inconsistent behavior, or competing validity).
6. Name the correct owner, callers to migrate, alternate producers to delete, and a focused cross-path regression.
7. State inspected boundaries and paths not traced. A clean result requires complete evidence within the declared scope; do not infer repository-wide uniqueness from a local search.

## DO NOT REPORT

Do not flag:
- multiple representations, read-only projections, or independently validating consumers of **one** established result;
- multiple owners of genuinely different lifecycle facts, scopes, or generations;
- test-only fixtures never admitted as production authority;
- harmless repeated checks that cannot establish accepted truth.

### Routing boundary

- `semantic-redecision-review`: the same question is answered again inside one authority chain but no second answer is accepted as authority.
- `resolved-fact-regression-review`: a consumer abandons an available resolved result for raw inputs, without a second independent accepted authority.
- `canonical-consumer-contract-review`: a consumer's obligation breaks across a legitimate refinement of its one owner's result.
- Use `state-authority-review`, `entrypoint-authority-review`, or `durable-commit-path-review` for their narrower state, entrypoint, or commit questions.

If multiple symptoms occur, name the primary ownership defect once and cross-reference secondary evidence; do not produce duplicate independent repairs.

## PREFER

One owner resolves the fact; downstream paths consume or validate that same result. Delete competing producers, fallback owners, and compensators—not merely the first failing call site.

For delegated execution: **resolve once → transport once → execute once → report once**.

## OUTPUT

Return `# Single Source of Truth Review` with fact/scope/generation, traced paths, authority map, accepted competing producers, material consequence, chosen owner, deletions, focused regression, and inspected/uninspected scope.

End with exactly one:
- `FINDING` — two reachable paths establish accepted authority for the same fact and scope;
- `CLEAN` — all in-scope owner/consumer paths were traced and only one accepted authority remains;
- `LEAVE ALONE` — suspected producers own demonstrably different facts/scopes;
- `INSUFFICIENT EVIDENCE` — reachable authority acceptance or scope cannot be established.
