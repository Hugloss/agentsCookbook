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

Trace what a real consumer reads, mutates and forwards, including lazy/optional paths and extension contracts. Show a concrete unnecessary dependency and the coupling, invalid state, setup cost or state exposure it causes. Establish that narrower existing inputs preserve the required consumer behavior. Field counts or the fraction used by one caller are leads, not proof.

## DO NOT REPORT

Do not report a broad aggregate whose breadth reflects one genuinely cohesive domain concept. Do not split contexts just to reduce field count.

## PREFER

Pass focused existing inputs or final semantic results. Remove forwarded/unused dependencies. Do not replace one giant context with a framework of mini-contexts.

## OUTPUT

Return `# Dependency Surface Review` with inspected consumer scope, supplied/used/forwarded dependencies, concrete unnecessary coupling, cohesive controls, target inputs and behavior-preserving verification.

Use `FINDING` for a demonstrated unnecessary dependency with a material consequence; `CLEAN` only after the declared consumer paths were traced and the supplied dependencies are justified; `LEAVE ALONE` for a justified cohesive aggregate; otherwise `INSUFFICIENT EVIDENCE`. Uninspected dynamic/extension consumers cannot be assumed to use no other fields.
