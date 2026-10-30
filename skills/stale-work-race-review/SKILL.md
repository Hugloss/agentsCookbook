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

Identify logical owner, operation identity, current-identity source, projection/side effect, existing guard, and a realistic harmful ordering. Use real production triggers such as retry, reconnect, rapid selection, duplicate delivery, or worker restart. Establish that replacement actually revokes the older work's authority; a newer request alone does not invalidate an independently owned earlier operation.

Follow the guard through the final effect. A current-owner check before an `await`, callback handoff, or remote write can race with replacement; prove atomic admission at the effect owner or an equivalent fence where required. Cancellation requested is not proof that already running work stopped. Distinguish a reachable source ordering from one actually executed in a test.

## DO NOT REPORT

Async code is not a race by itself. Do not confirm a race without an executable ordering that changes correctness. Teardown alone is not proof if queued callbacks can still run.

## PREFER

Use exact owner tokens, generations/sequences, operation IDs, compare-and-transition, current-owner checks, immutable terminal results, or owner-scoped cancellation. Prefer deterministic race tests over sleeps.

## OUTPUT

Return `# Stale Work Race Review` with the inspected owners/effect paths, proved races, unresolved leads, safe guards, and deterministic tests. Every finding: owner, identity, projection, ordering, missing guard, consequence, smallest fix. Keep potential races and fragile-looking guards as leads unless the harmful ordering is established.

Use `FINDING` for a proved stale-owner effect. Use `CLEAN` only when the declared replacement and effect paths are completely traced, or `LEAVE ALONE` when an inspected guard or independent ownership makes the suspected ordering safe. Missing effect-owner or cancellation semantics require `INSUFFICIENT EVIDENCE` when no finding is established; do not turn a local race review into system-wide safety.
