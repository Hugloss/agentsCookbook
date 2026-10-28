---
name: deterministic-causality-test-review
description: Finds sleeps, polling, retries, timeout inflation, or scheduler luck used where tests should control causal events directly.
license: MIT
---

# Deterministic Causality Test Review

Standalone, read-only timing/nondeterminism review.

## INVARIANT

> **Tests should control causality, not hope timing produces it.**

## HUNT

Hunt for sleeps, arbitrary delays, polling, retry-until loops, timeout inflation, timestamp ordering, uncontrolled background work, and race-sensitive callback delivery. Translate each wait into the actual event relationship it needs.

## PROVE

Show the required causal sequence and whether production exposes an observable completion/transition contract. Reproduce flakiness deterministically where evidence permits.

## DO NOT REPORT

Do not replace one arbitrary delay with a longer one. Do not use fake time when the behavior under test is real scheduler/integration timing.

Do not report bounded polling of an external, operation-correlated completion state merely because it polls when no direct completion signal is available. Require a deadline, bounded reads, and useful failure evidence. A polling interval or a test of an actual timer contract is not an arbitrary completion assumption.

## PREFER

Use controlled promises, barriers, fake clocks where appropriate, explicit callbacks, sequence/operation IDs, and observable completion states. Fix missing production completion contracts when that is the root cause.

Use `event-driven-test-verification` when asked to construct the integration observer; retain this skill for diagnosing the causal defect.

## OUTPUT

Return `# Deterministic Causality Test Review` with timing smells, real causal events, missing contracts, deterministic test pattern, production changes if needed, and verification.
