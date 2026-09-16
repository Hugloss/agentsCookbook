---
name: code-performance-optimization-audit
description: Finds meaningful scaling, repeated-work, I/O, memory, batching, caching, and hot-path performance waste.
license: MIT
---

# Code Performance Optimization Audit

Standalone, read-only performance audit. Find work the system does not need to do and explain how cost multiplies under realistic workloads.

Do not assume a parent flow, run store, or specific repository architecture. Preserve correctness, determinism, freshness, observable behavior, and ownership boundaries.

## Performance model

Before recommending changes:

- Trace normal entry points and likely hot paths.
- Estimate `cost per call × realistic call count` when evidence permits.
- Identify costs that grow with repository/input/graph/result/workload size.
- Look for loop-invariant work, nested scans, repeated traversal, N+1 I/O, repeated parsing/hashing/normalization/sorting/serialization, unnecessary materialization/copies, subprocess startup, and lock contention.
- Separate measured evidence, repository facts, and reasoned estimates. Never invent workload sizes or benchmark results.

## Preferred optimization order

```text
eliminate unnecessary work
→ improve the algorithm
→ improve the data structure
→ reduce I/O
→ reuse trustworthy results
→ batch bounded work
→ optimize constants
```

For caches require explicit key/identity semantics, owner, lifetime/size bound, invalidation/freshness rule, concurrency behavior, memory/storage cost, and stale-value policy. Reject caches whose freshness cannot be proved.

For concurrency require bounds, determinism, cancellation/error propagation, resource pressure, race handling, and evidence that concurrency solves the real bottleneck rather than hiding a poor algorithm.

Prefer one authoritative scan/index/projection boundary over repeated rediscovery when repository evidence supports it.

## Priorities

- `P0`: algorithmic/scaling defect likely to degrade dramatically with workload growth.
- `P1`: high-value repeated work in realistic usage.
- `P2`: meaningful constant-factor improvement.
- `P3`: micro-optimization; do not recommend implementation without measurement or a simultaneous clarity benefit.

## Required finding fields

For each material opportunity provide: Location; Current behavior; Performance problem; Current complexity/cost; Proposed complexity/cost; Proposed change and ownership boundary; Expected impact; Workload affected; Correctness risks; Measurement; Priority.

Validation must cover semantic correctness, realistic workload sizes, deterministic output where required, runtime/memory, invalidation for cached/incremental results, and concurrency behavior when relevant.

Never edit files, provide patches, invoke agents, or claim an optimization has been implemented.

## Output

Return `# Code Performance Optimization Audit` with:

- `## Performance Model`
- `## Findings`
- `## Final Performance Map` — Priority, Area, Current Cost, Proposed Cost, Expected Impact, Confidence
- `## Smallest Coherent Optimization Sequence`
- `## Guardrails`

If evidence is insufficient for a meaningful recommendation, say so instead of manufacturing micro-optimizations.
