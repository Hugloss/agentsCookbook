---
name: code-performance-optimization-audit
description: Finds material runtime cost from scaling, repeated work, I/O, memory, batching, caching, and contention.
license: MIT
---

# Code Performance Optimization Audit

Standalone, read-only runtime performance review. Measure or bound real cost before proposing optimization.

## INVARIANT

> **Remove unnecessary work before making necessary work faster.**

## HUNT

Trace real entry points and hot paths. Hunt for:
- poor asymptotic behavior and nested scans;
- N+1 I/O, repeated parsing/hashing/sorting/serialization;
- repeated traversal, materialization, copies, subprocess startup, and lock contention;
- work whose cost multiplies with realistic repository, graph, request, or result size.

## PROVE

For each finding show the production path, cost per call, realistic call multiplier when known, and why the work is unnecessary or poorly scaled. Separate measured evidence from reasoned estimates. Never invent benchmark numbers.

## DO NOT REPORT

Do not report unmeasured micro-optimizations, speculative concurrency, or caches without provable identity, freshness, lifetime, and invalidation semantics. Repeated observation that creates one-operation consistency risk belongs primarily in `single-observation-review`.

## PREFER

Use this order: eliminate work → improve algorithm → improve data structure → reduce I/O → reuse trustworthy results → bounded batching → constants. Preserve correctness, freshness, determinism, and ownership.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, inspect the changed production paths and supplied implementation evidence for material runtime cost. Report only costs supported by the change, its callers, or a realistic workload. Do not require a measured win when no material performance issue is found.

Return `# Build Performance Review` with findings, missing measurement or evidence, concrete fixes, and remaining risk. Use `None` when no material performance issue is supported.

## OUTPUT

Otherwise return `# Code Performance Optimization Audit` with `Performance Model`, `Findings`, `Final Performance Map`, and `Smallest Coherent Optimization Sequence`. Each finding: location, current cost, root cause, proposed cost, expected impact, correctness risk, measurement, priority.
