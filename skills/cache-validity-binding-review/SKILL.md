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

Identify one semantic dimension omitted from the key or validity check. Change only that dimension while preserving the cache key and show how stale or wrong semantics can be returned.

## DO NOT REPORT

Do not report unkeyed timing, counters, or other performance-only diagnostics. Do not require irrelevant environment values in a semantic cache key.

## PREFER

Keep caches derived and disposable. Bind exact semantic inputs and authoritative generation, and revalidate persisted payload integrity on read.

## OUTPUT

Return `# Cache Validity Binding Review` with cache owner, key fields, omitted semantic dimension, stale-hit path, consequence, corrected binding, verification.
