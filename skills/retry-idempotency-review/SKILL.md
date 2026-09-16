---
name: retry-idempotency-review
description: Finds retries, redelivery, or duplicate invocation that can repeat effects meant to happen once per logical operation.
license: MIT
---

# Retry Idempotency Review

Standalone, read-only duplicate-effect review.

## INVARIANT

> **Repeating the same logical operation must not repeat effects that are supposed to happen once.**

## HUNT

Hunt production paths involving:
- HTTP/client retry after timeout;
- queue or webhook redelivery;
- worker restart or resume;
- reconnect and replay;
- duplicate callback delivery;
- double submit;
- at-least-once processing;
- recovery that re-enters normal completion.

Focus on effects such as durable writes, event publication, notifications, billing, allocation, creation, or irreversible external calls.

## PROVE

Identify the logical operation identity, the repeated delivery/execution path, the one-shot effect, and the missing or insufficient duplicate guard. Show one realistic sequence in which the same logical operation performs the effect twice.

## DO NOT REPORT

Do not report two genuinely distinct operations or behavior that is intentionally repeatable. Superseded old work belongs to `stale-work-race-review` unless the same logical operation is being replayed.

## PREFER

Enforce idempotency at the effect owner with the existing operation identity, compare/create-only semantics, uniqueness, or an already-owned terminal transition. Do not add a generic global deduplication service when a local authority can reject the duplicate.

## OUTPUT

Return `# Retry Idempotency Review` with findings: logical operation, duplicate trigger, repeated effect, current guard, real consequence, canonical idempotency boundary, code/retry handling that can disappear, deterministic replay test.
