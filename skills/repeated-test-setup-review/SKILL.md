---
name: repeated-test-setup-review
description: Finds expensive application, database, repository, browser, or fixture setup rebuilt across tests without semantic need.
license: MIT
---

# Repeated Test Setup Review

Standalone, read-only test-construction cost review.

## INVARIANT

> **Repeated setup should represent required isolation, not repeated architecture construction.**

## HUNT

Trace setup separately from behavior execution, using existing timings when helpful. Hunt repeated app bootstrap, DB/schema setup, repository indexing, config loading, dependency discovery, browser/server startup, auth/session setup, and large fixture graph construction. An inspected fixture graph can establish redundant construction without a profiling prerequisite.

## PROVE

For each repeated setup, identify the actual invocation/worker/parameter lifetime and prove whether isolation or the tested lifecycle requires rebuilding it. Separate reusable infrastructure/schema from mutable per-test state and live clients. Identify the smallest real dependency and a reset/ownership contract that preserves isolation; fixture scope alone is not that proof.

## DO NOT REPORT

Do not trade isolation for hidden shared mutable fixtures. Do not report clean-room setup that is essential to the integration behavior, migration test, or unresettable state. One session-scoped resource per parallel worker is not automatically accidental duplication.

## PREFER

Prefer cheap production construction, narrow fixtures, and explicit dependencies. Share only immutable/safely isolated setup.

## OUTPUT

Return `# Repeated Test Setup Review` with inspected fixture consumers/lifetimes, demonstrated repetition, required versus accidental construction, safe reuse boundary, correction, and functional isolation checks. Timings are optional; quantified speedup claims require comparable measurements.

Use `FINDING` for demonstrated unnecessary reconstruction; bounded `CLEAN` or `LEAVE ALONE` requires inspected construction and isolation/reset ownership. If the reset, worker, or client lifetime cannot be established, retain `INSUFFICIENT EVIDENCE` instead of recommending broader sharing.
