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

Establish which effect must be once-only and the supported replay window. Identify the logical operation identity and its tenant/operation scope, the repeated delivery/execution path, and the missing or insufficient duplicate guard. Show one realistic sequence in which the same logical operation performs the effect twice.

Inspect concurrent retries as well as sequential replay. Read-then-check admission can race; a unique request row alone does not make a separately committed effect atomic. Follow uncertain outcomes such as a remote success followed by a lost response, and the effect owner's actual idempotency/reconciliation contract. Verify that the key and deduplication evidence survive the permitted restart, redrive, and retention horizon. Distinct payloads under one key require the established conflict/reprocessing semantics; a new random key on every retry cannot identify the same operation.

## DO NOT REPORT

Do not report two genuinely distinct operations, repeated pure computation, or behavior that is intentionally repeatable. Preserve an existing atomic conditional write or effect-owned idempotency contract; no separate registry is required when that owner already prevents the duplicate. Superseded old work belongs to `stale-work-race-review` unless the same logical operation is being replayed.

## PREFER

Enforce idempotency at the effect owner with the existing operation identity, compare/create-only semantics, uniqueness, or an already-owned terminal transition. Do not add a generic global deduplication service when a local authority can reject the duplicate.

## OUTPUT

Return `# Retry Idempotency Review` with the inspected effect/replay scope and findings: logical operation, duplicate trigger, repeated effect, current guard, real consequence, canonical idempotency boundary, code/retry handling that can disappear, and deterministic duplicate/control test.

Use `FINDING` for an established repeat of a protected effect; `CLEAN` requires the declared identity, admission, effect, and replay/recovery paths to be completely traced. Use `LEAVE ALONE` for a positively replay-safe owner. Missing external-effect semantics or retention policy is `INSUFFICIENT EVIDENCE` when no violation is proved, never assumed exactly-once behavior.
