---
name: stale-work-race-review
description: Finds async causality races where older work can mutate state owned by a newer identity, generation, or operation.
license: MIT
---

# Stale Work Race Review

Standalone, read-only system-wide race review across frontend, backend, workers, queues, callbacks, retries, schedulers, and persistence.

## INVARIANT

> **Work from an older owner or generation must not mutate state owned by a newer one.**

## HUNT

Hunt for async work that captures identity, waits, then commits:
- requests, jobs, workers, queues, callbacks, polling, subscriptions, retries, recovery;
- reads followed by writes;
- terminal callbacks or persistence after replacement.
Construct `A starts → B supersedes A → B commits → A completes → A attempts commit`.

## PROVE

Identify logical owner, operation identity, current-identity source, projection/side effect, existing guard, and a realistic harmful ordering. Use real production triggers such as retry, reconnect, rapid selection, duplicate delivery, or worker restart.

## DO NOT REPORT

Async code is not a race by itself. Do not confirm a race without an executable ordering that changes correctness. Teardown alone is not proof if queued callbacks can still run.

## PREFER

Use exact owner tokens, generations/sequences, operation IDs, compare-and-transition, current-owner checks, immutable terminal results, or owner-scoped cancellation. Prefer deterministic race tests over sleeps.

## OUTPUT

Return `# Stale Work Race Review` with confirmed races, potential races, fragile guards, proven-safe paths, and deterministic tests. Every finding: owner, identity, projection, ordering, missing guard, consequence, smallest fix.
