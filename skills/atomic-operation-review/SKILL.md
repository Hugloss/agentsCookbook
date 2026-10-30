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

Establish the required all-or-nothing or staged contract independently of the candidate's success path. Identify the operation owner, ordered effects, and one realistic failure cut between them. Show the partial state that survives or becomes observable before compensation, and how another caller can act on it.

Follow actual commit/visibility boundaries and recovery. A transaction protects only its participating effects; a cleanup attempt cannot retract an already observed event or remote action. Conversely, explicit recoverable staged progress may satisfy the contract without cross-system atomicity. Unknown remote semantics are an evidence gap, not automatically a proved partial commit.

## DO NOT REPORT

Do not report deliberately staged workflows whose intermediate states are explicit, durable, observable, and recoverable. Multiple commit callers belong to `durable-commit-path-review` unless the defect is partial commit within one legitimate path.

## PREFER

Use the smallest existing atomic boundary that can own the operation. Where true atomicity is impossible, make staged state and recovery explicit. Do not introduce a generic transaction or saga framework unless the domain actually requires one.

## OUTPUT

Return `# Atomic Operation Review` with the inspected operation/observer scope and findings: required contract, effect sequence, failure cut, observable partial state, real consequence, target boundary/recovery, code or compensation logic that can disappear, deterministic verification.

Use `FINDING` for a proved prohibited partial outcome. `CLEAN` requires all required effects, relevant failure cuts, and recovery/observation paths in the declared scope to be inspected; `LEAVE ALONE` requires a supported atomic or staged design. Use `INSUFFICIENT EVIDENCE` when missing visibility or recovery semantics prevent a conclusion and no defect is proved.
