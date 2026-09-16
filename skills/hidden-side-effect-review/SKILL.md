---
name: hidden-side-effect-review
description: Finds externally visible side effects hidden behind APIs whose names, types, or boundaries appear observational or pure.
license: MIT
---

# Hidden Side Effect Review

Standalone, read-only effect-visibility review.

## INVARIANT

> **A caller should be able to tell when an operation can change the world.**

## HUNT

Hunt for writes, network calls, subprocesses, scheduling, event emission, navigation, cache/global mutation, retries, or refresh hidden inside reads, constructors, normalization, getters, parsing, conversion, or generic helpers.

## PROVE

Trace a real production call path and show why the caller cannot reasonably see or order the side effect from the boundary. Explain the concrete sequencing, failure, or ownership risk.

## DO NOT REPORT

Do not report an effect merely because it is encapsulated. The issue is misleading semantics, hidden ordering, or unclear ownership.

## PREFER

Make the effect explicit at the existing semantic owner. Split pure decision from effect only at a natural boundary. Do not create an effect-manager abstraction.

## OUTPUT

Return `# Hidden Side Effect Review` with call path, hidden effect, owner, consequence, explicit boundary, code removable after clarification, and verification.
