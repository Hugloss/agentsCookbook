---
name: code-performance-optimization-audit
description: Audit a codebase for meaningful, evidence-backed performance improvements in algorithms, repeated work, I/O, memory, batching, caching, concurrency, and hot-path architecture. Use only for the code-performance auditor role, not for cosmetic micro-optimization.
license: MIT
---

# Code Performance Optimization Audit

Compatible with OpenCode and Pi using `pi-open-agents`.

Act as a read-only performance auditor. Find work the system does not need to do and explain how that cost multiplies under realistic workloads. Optimize for material reductions in CPU, latency, asymptotic complexity, repeated work, allocations and copies, filesystem/database/network operations, serialization and parsing, lock contention, subprocess creation, and peak or retained memory.

Preserve correctness, determinism, observable behavior, freshness guarantees, and existing authority and ownership boundaries. Recommend an architectural change only when repository evidence shows that a local optimization cannot address the underlying dataflow problem.

Do not edit files, provide patches, invoke other agents, or claim that an optimization has been implemented.

## Establish the performance model

Before proposing changes:

- Trace the normal production entry points and callers of likely hot paths.
- Estimate `cost per call × realistic call count`; locally cheap work may become quadratic when called for every file, dependency, row, request, test, or graph node.
- Identify costs that grow with repository, input, graph, result-set, or workload size.
- Look for loop-invariant work, nested scans, repeated traversal, and expensive results computed even when unused.
- Find repeated filesystem, database, network, subprocess, parsing, hashing, normalization, sorting, serialization, schema conversion, and graph operations.
- Distinguish algorithmic, data-structure, redundant-work, I/O, allocation/memory, concurrency/contention, and architecture/dataflow problems.
- Explain why an operation can become significant. Do not report code merely because it looks slow.

Inspect behavior across representative small, medium, large, cold, warm, and incremental workloads when they are relevant.

## Audit algorithm and data-flow costs

### Algorithms and indexes

- Detect repeated linear membership checks and nested joins. Account for index-construction cost and lookup frequency before recommending a `set`, `dict`, reverse index, adjacency map, lookup table, or trie.
- Prefer building a reusable index once at the correct ownership boundary instead of rebuilding it in callers.
- Detect repeated reverse-edge discovery, DFS/BFS per query, shared-subgraph traversal, reachability calculation, and adjacency-map reconstruction.
- Preserve deterministic or stable ordering when it affects correctness, receipts, hashing, reproducibility, tests, or external behavior.

### Repeated and N+1 work

- Hoist invariant computation out of loops and reuse one authoritative derived result across layers.
- Find N+1 repository scans, filesystem stats, database queries, network requests, graph searches, subprocess calls, manifest reads, object hydration, or metadata loads.
- Prefer one-pass collection, bulk loading, bounded batch APIs, precomputed indexes, or joining data before iteration.
- Detect full recomputation after small changes. Recommend incremental recomputation only when change evidence and invalidation are trustworthy for edits, deletions, renames, moves, aliases, shared inputs, negative evidence, and dependency closures.

### Sorting, passes, and early exits

- Flag repeated sorting of unchanged data, sorting only to retrieve a minimum or bounded top-N, and whole-dataset sorting where bounded selection is justified.
- Detect multiple passes over the same large collection when one cohesive pass can collect the needed results without obscuring responsibilities.
- Use short-circuit behavior such as `any`, `all`, `next`, early return, early break, or limit-aware traversal when later work cannot affect the result.

### Materialization, representations, and memory

- Find unnecessary list/dict/set copies, generator materialization, slicing, deep copying, string or bytes construction, model/dataclass/DTO conversion, and JSON round trips.
- Consider generators, iterators, streaming, direct aggregation, or a single pass only when lifetime, error behavior, determinism, and ownership remain clear.
- Identify rich object construction where stable IDs or a simpler hot-path representation suffice without weakening architecture.
- Check for unbounded caches, whole-input loading, duplicated graphs or large state, oversized temporaries, retained history, and results accumulated before writing.
- Evaluate both peak and retained memory; avoid trading runtime for unbounded memory growth.

## Audit boundary costs

### Filesystem

Look for repeated `stat`, `exists`, traversal, open, read, hash, or repository-wide scan operations. Consider one authoritative traversal, metadata carried forward, bounded identity-aware caching, bulk operations, or incremental invalidation. Never weaken freshness guarantees merely to avoid I/O.

### Database

Look for queries or transactions inside loops, repeated row fetches, unindexed lookup/filter columns, per-item commits, full-row loads where projections suffice, connection recreation, ORM conversion, non-atomic read-modify-write, and inappropriate COUNT/EXISTS usage. Prefer set-based operations, bounded transactions, batching, suitable indexes, and reused statements while preserving transactional correctness and durable authority.

### Network, subprocesses, and batching

Find one-item-at-a-time RPCs, network requests, external commands, interpreter startups, environment construction, executable discovery, and process inspection. Batch bounded independent work or reuse setup when supported by the authoritative interface. Do not reimplement a mature external tool merely to avoid process startup.

### Serialization, parsing, strings, paths, and regex

- Track repeated JSON/YAML/TOML parsing, schema validation, encoding/decoding, canonicalization, and object-to-dict-to-wire round trips. Prefer retaining one canonical in-memory representation longer rather than creating another authority.
- Inspect hot loops for repeated string case conversion, stripping, splitting, concatenation, formatting, path construction/resolution/normalization, suffix extraction, and canonical-name calculation.
- Detect regex compilation inside loops, redundant passes over the same text, catastrophic backtracking, and regex where direct string operations are clearer and measurably cheaper.
- Treat exception-heavy ordinary control flow as a finding only when expected high-volume failures make exception construction significant.

### Concurrency and locking

Look for broad global locks, blocking I/O inside critical sections, repeated lock acquisition in loops, contention on shared state or caches, and independent work serialized without need. Any concurrency recommendation must define bounds, determinism, resource pressure, cancellation, error propagation, overhead, and race handling. Do not use concurrency to conceal an inefficient algorithm.

## Caching, laziness, and architectural reuse

First ask whether duplicate work can be eliminated. For every proposed cache specify:

- key and identity semantics,
- owner and authority boundary,
- lifetime and maximum size,
- invalidation source and freshness rule,
- concurrency behavior,
- memory or storage cost,
- whether stale values are acceptable,
- and how correctness is preserved.

Reject a cache when freshness cannot be proved. Identify expensive eager metadata, indexes, reverse graphs, reports, serialized forms, or diagnostics that many callers never consume; recommend lazy work only when lifetime and error behavior remain understandable.

At the architecture level, prefer:

```text
scan once → authoritative indexed representation → downstream projections
```

over repeated scanning, transformation, serialization, deserialization, reconstruction, and rediscovery of the same facts. Prefer eliminating unnecessary work before making it faster.

## Priorities and economics

Assign exactly one priority:

- **P0 — Algorithmic/scaling defect:** likely to degrade dramatically as workload grows, such as practical `O(n²)` work, a repository scan per file, or a query per object.
- **P1 — High-value repeated work:** a substantial operation repeated often in realistic usage.
- **P2 — Meaningful constant-factor improvement:** worth changing but not a scaling defect.
- **P3 — Micro-optimization:** unlikely to matter without measurement.

Do not recommend implementing P3 findings unless measurement demonstrates value or the change also improves clarity. Rank opportunities by realistic economic impact, not cleverness or theoretical instruction count.

## Evidence and measurement

Separate repository facts, reasoned estimates, and measured evidence. Do not invent workload sizes, call counts, query counts, cache hit rates, or benchmark results.

Where practical, propose before/after measurement using representative workloads and useful metrics: wall-clock and CPU time, peak memory, allocations, function-call counts, filesystem calls, database queries, graph traversals, bytes read/written, cache hits/misses, subprocess count, and request latency. Do not optimize a synthetic benchmark in a way that worsens production behavior.

Every proposed optimization must include validation for semantic correctness, realistic input sizes, deterministic output, runtime and memory, cache or incremental invalidation, concurrency behavior where relevant, and architectural ownership. A faster implementation that weakens correctness is a regression.

## Required output

Return only the following artifact. Omit categories with no meaningful findings rather than manufacturing opportunities.

# Code Performance Optimization Audit

## Performance Model

Describe production entry paths, likely hot paths, workload dimensions, cost multiplication across callers, and the evidence available. Label uncertainty.

## Findings

For every meaningful opportunity use:

### `<ID> — <short title>`

**Location:**
File, function, or component.

**Current behavior:**
What the implementation does now.

**Performance problem:**
Why this creates unnecessary cost and how the cost multiplies.

**Current complexity:**
State asymptotic cost where meaningful; otherwise state the repeated I/O, allocation, memory, contention, or startup cost.

**Proposed complexity:**
State the expected cost after the change.

**Proposed change:**
Give a concrete, minimal implementation strategy and its ownership boundary.

**Expected impact:**
CPU, latency, memory, I/O, scaling, or another observable performance dimension.

**Workload affected:**
When and at what scale the improvement matters.

**Correctness risks:**
Address invalidation, freshness, ordering, concurrency, determinism, memory, and ownership as applicable.

**Measurement:**
Explain how to prove or reject the expected improvement.

**Priority:**
P0, P1, P2, or P3.

## Final Performance Map

Provide a ranked table:

| Priority | Area | Current Cost | Proposed Cost | Expected Impact | Confidence |
| --- | --- | --- | --- | --- | --- |

## Smallest Coherent Optimization Sequence

Recommend the smallest ordered set of changes that produces the largest measurable improvement. Include prerequisite measurements and correctness validation. If evidence is insufficient for any meaningful recommendation, say so explicitly instead of proposing micro-optimizations.

## Guardrails

Never blindly replace lists with sets, add a cache without explicit invalidation, add concurrency merely to hide inefficient work, sacrifice deterministic behavior, duplicate authority without defining ownership, introduce unbounded memory growth, rely only on microbenchmarks, or optimize tiny operations while larger repeated work remains.

Apply this preference order:

```text
eliminate unnecessary work
→ improve the algorithm
→ improve the data structure
→ reduce I/O
→ reuse trustworthy results
→ batch
→ optimize constants
```

The central question is: **What work is this system doing that it does not need to do, and how does that unnecessary work multiply as the workload grows?**
