---
name: dependency-surface-review
description: Finds APIs, contexts, hooks, or dependency bags that expose far more subsystem state than a behavior actually needs.
license: MIT
---

# Dependency Surface Review

Standalone, read-only coupling-surface review.

## INVARIANT

> **A behavior should receive what it needs, not the internal state of an entire subsystem.**

## HUNT

Hunt for huge context objects, callback bags, orchestrators, broad hook returns, optional capability surfaces, and fixtures where most consumers use a small subset. Record dependencies supplied, consumed, and merely forwarded.

## PROVE

Show how the oversized surface increases coupling, invalid combinations, setup cost, test complexity, or internal-state leakage on a real operation.

## DO NOT REPORT

Do not report a broad aggregate whose breadth reflects one genuinely cohesive domain concept. Do not split contexts just to reduce field count.

## PREFER

Pass focused existing inputs or final semantic results. Remove forwarded/unused dependencies. Do not replace one giant context with a framework of mini-contexts.

## OUTPUT

Return `# Dependency Surface Review` with boundary, supplied/used/forwarded dependency map, concrete coupling cost, target inputs, removals, and verification.
