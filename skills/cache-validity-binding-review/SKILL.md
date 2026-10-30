---
name: cache-validity-binding-review
description: Finds cache hits whose key or validity check omits semantic inputs, authority generation, policy, configuration, or source identity.
license: MIT
---

# Cache Validity Binding Review

Standalone, read-only cache correctness review.

## INVARIANT

> **A cached result is reusable only when its key and validity checks bind every semantic input that could change that result.**

## HUNT

Hunt for caches missing:
- source or repository identity;
- generation/revision;
- task/query parameters;
- policy, visibility, admission, or configuration;
- schema, producer, tool, or mode identity when semantically relevant;
- invalidation for durable state changes;
- integrity revalidation of persisted cache payloads.

## PROVE

Identify one semantic dimension unprotected by the combined key, invalidation, and read-time validity contract. Change only that dimension, trace any invalidation or revalidation it triggers, and show a reachable hit that still returns stale or wrong semantics. A field missing from the key is not sufficient proof when another existing guard prevents that reuse.

## DO NOT REPORT

Do not report unkeyed timing, counters, or other performance-only diagnostics. Do not require irrelevant environment values in a semantic cache key.

## PREFER

Keep caches derived and disposable. Bind exact semantic inputs and authoritative generation, and revalidate persisted payload integrity on read.

## OUTPUT

Return `# Cache Validity Binding Review` with cache owner, key fields, omitted semantic dimension, stale-hit path, consequence, corrected binding, verification.

Use `FINDING` for a proved stale reuse path, or `LEAVE ALONE` when the existing validity/invalidation owner prevents it. `CLEAN` requires tracing the named cache's relevant mutation and read paths; unknown invalidation behavior is `INSUFFICIENT EVIDENCE`.
