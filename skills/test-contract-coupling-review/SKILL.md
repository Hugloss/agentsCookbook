---
name: test-contract-coupling-review
description: Finds tests that freeze private helpers, call order, source strings, wrappers, or internal choreography instead of real contracts.
license: MIT
---

# Test Contract Coupling Review

Standalone, read-only test-contract review.

## INVARIANT

> **Tests should protect behavior and real architectural boundaries, not freeze private choreography.**

## HUNT

Hunt assertions on private helper calls, exact internal call order, source strings, wrapper counts, private intermediate objects, internal module names, and large mock trees that mirror implementation.

## PROVE

Ask whether a behavior-preserving internal simplification would break the test. If yes, prove whether the asserted detail is a genuine architecture invariant or accidental structure.

## DO NOT REPORT

Do not remove narrow structural tests that enforce a real boundary or ban, such as forbidding UI code from importing a persistence client.

## PREFER

Assert externally meaningful behavior and small explicit architectural constraints. Delete mocks/assertions that exist only to mirror current internals.

## OUTPUT

Return `# Test Contract Coupling Review` with coupled tests, frozen detail, real contract, false-failure risk, replacement assertion, removable mocks/guards, and verification.
