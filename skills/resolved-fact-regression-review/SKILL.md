---
name: resolved-fact-regression-review
description: Finds downstream code that falls back from an already-resolved semantic fact to raw inputs and decides it again.
license: MIT
---

# Resolved Fact Regression Review

Standalone, read-only semantic-boundary review.

## INVARIANT

> **Once a fact is resolved semantically, downstream code should not regress to raw inputs and resolve it again.**

## HUNT

Trace important flows as `RAW → VALIDATED → RESOLVED → EXECUTION/DURABLE RESULT`. Hunt for downstream code that returns to:
- raw paths or names;
- flags or payload fields;
- low-level persistence columns;
- unresolved capabilities/config;
- source data already converted into an authoritative identity or decision.

## PROVE

Show where the fact became authoritative, where that result is discarded, what raw inputs are reinterpreted, and how this can drift or lengthen the call chain.

## DO NOT REPORT

Do not report a downstream integrity assertion that checks the resolved fact without changing its meaning.

## PREFER

Pass the final semantic result. Remove raw ingredients and re-resolution logic from later APIs when they are no longer needed.

## OUTPUT

Return `# Resolved Fact Regression Review` with fact-flow traces, regression points, authoritative boundary, code to remove, and proof that downstream code consumes the resolved result.
