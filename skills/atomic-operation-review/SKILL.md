---
name: atomic-operation-review
description: Finds logical operations that can expose partial externally visible state when one step fails mid-commit.
license: MIT
---

# Atomic Operation Review

Standalone, read-only partial-commit review.

## INVARIANT

> **One logical operation must not expose half of its required outcome unless partial progress is an explicit durable state.**

## HUNT

Hunt real production paths that combine multiple externally visible effects:
- database + filesystem;
- state write + event/outbox;
- reservation + publication;
- metadata + content;
- multiple durable rows or resources;
- write sequences with cleanup or compensation after failure.

## PROVE

Identify the operation owner, ordered effects, and one realistic failure cut between them. Show the partial state that survives and how another caller can observe or act on it.

## DO NOT REPORT

Do not report deliberately staged workflows whose intermediate states are explicit, durable, observable, and recoverable. Multiple commit callers belong to `durable-commit-path-review` unless the defect is partial commit within one legitimate path.

## PREFER

Use the smallest existing atomic boundary that can own the operation. Where true atomicity is impossible, make staged state and recovery explicit. Do not introduce a generic transaction or saga framework unless the domain actually requires one.

## OUTPUT

Return `# Atomic Operation Review` with findings: logical operation, effect sequence, failure cut, surviving partial state, real consequence, target boundary/recovery, code or compensation logic that can disappear, deterministic verification.
