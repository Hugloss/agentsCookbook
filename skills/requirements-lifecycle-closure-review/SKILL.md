---
name: requirements-lifecycle-closure-review
description: Finds lifecycle requirements that go silent on partial effects, races, crashes, teardown, unresolved state, or recovery.
license: MIT
---

# Requirements Lifecycle Closure Review

Standalone, read-only review of stateful or effectful requirements, architecture, protocol, and execution specifications.

Use this skill before implementation when the specification defines operations that can bind resources, execute work, persist state, coordinate asynchronous actors, or require teardown/recovery.

## INVARIANT

> **A lifecycle contract is closed only when every effectful phase and transition has deterministic ownership, partial-failure behavior, causal ordering, teardown, evidence, and recovery semantics without requiring runtime improvisation.**

A strong specification must remain truthful not only on its happy path, but when work stops between any two externally meaningful effects.

## HUNT

Trace the declared lifecycle from creation through terminal evidence. Hunt for places where the specification goes silent about:

- a phase that can create physical, durable, external, or security-relevant effects before the named "work" begins;
- failure after some effects succeeded but before the phase completed;
- cancellation, timeout, revocation, or stale authority during admission, binding, execution, or teardown;
- two terminal/significant events that can race without one authoritative ordering owner;
- an authority/envelope transition whose trigger or exact ordering is implicit;
- downstream units that never start after an earlier failure but have no explicit state or cause;
- an aggregate outcome whose rollup from child/unit outcomes is not deterministic;
- an unknown event or schema member whose default treatment is unspecified;
- a controlling process or control plane dying before authenticated terminal evidence exists;
- effect-producing resources created without durable ownership established before creation;
- teardown or revocation that is attempted but cannot be proven complete;
- recovery that can access prior-run resources without explicit cross-run authority;
- future-produced artifacts consumed by mutable location instead of pre-admitted lineage plus sealed identity/type;
- evidence/UI claims that are stronger than the evidence strength actually available;
- an append-only history that detects interior gaps but not tail truncation or replay.

Focus on lifecycle closure. Do not turn the review into a generic architecture critique.

## PROVE

For each finding identify:

- **Phase or transition** — the exact lifecycle boundary under review.
- **Owner** — the one semantic component that should own the missing decision.
- **Effects before failure** — resources, durable state, external effects, or authority that may already exist.
- **Failure cut** — one concrete point where execution can stop or race.
- **Current ambiguity** — the two or more plausible interpretations the specification permits.
- **Required state/outcome** — how the contract should represent the path without falsifying prior history.
- **Teardown/quiescence rule** — what must be cleaned up or proven stopped, and what happens if that proof fails.
- **Ordering rule** — when races are involved, the authoritative sequence/transaction/log owner; wall-clock time alone is not sufficient unless the contract makes it authoritative.
- **Evidence rule** — what receipt, journal, provenance, or evidence strength proves the result.
- **Recovery rule** — when residual authority can survive, how later recovery obtains explicit authority without rewriting the original history.
- **Acceptance test** — one deterministic test vector that would fail before the specification is closed.

A finding requires a real reachable lifecycle path or a requirement that permits one. Do not report hypothetical states already made impossible by an explicit invariant.

## CLOSURE CHECK

For each effectful phase, verify that the specification can answer all materially applicable questions:

1. What state exists before the phase?
2. Who owns its semantics?
3. Can it create effects before completion?
4. What happens if it fails before any effect?
5. What happens if it fails after partial effects?
6. What happens on cancellation or timeout?
7. What happens if its owner crashes?
8. Who owns teardown?
9. What if teardown cannot be proven?
10. Who orders races with completion/failure/cancellation?
11. Which authority envelope applies at each ordered event?
12. What evidence proves the resulting state?
13. Can later recovery touch its residual resources, and under what authority?
14. What deterministic acceptance test proves the edge?

Not every simple specification needs every mechanism. Apply only questions made relevant by the effects and concurrency the contract actually permits.

## DO NOT REPORT

Do not report:

- generic missing implementation tasks, callers, migrations, docs, or validation that do not expose an ambiguous lifecycle state; those belong to `plan-gap-scout`;
- a plan merely because it lacks low-level code details when its lifecycle contract is already deterministic;
- an implementation resource leak when the requirements already define correct ownership/teardown; `resource-lifetime-review` owns the implementation defect;
- inconsistent failure translation across existing code layers; `failure-contract-review` owns that semantic divergence;
- partial durable commit inside one implementation path when the requirements already model it correctly; `atomic-operation-review` owns the implementation defect;
- a state representation that can express impossible combinations independent of transition closure; `invalid-state-model-review` owns that question;
- a general final-handoff omission that does not create lifecycle ambiguity; `plan-contract-guard` or `red-team-leftover-gate` owns those concerns;
- absence of recovery, journal, signatures, sequencing, leases, or write-ahead ownership when the reviewed system has no effectful/asynchronous path that requires them.

Do not require distributed-systems machinery for a simple synchronous operation just to make the prompt look rigorous.

## PREFER

Prefer the smallest specification correction that closes the real lifecycle seam:

- name the missing state instead of adding a catch-all manager;
- define one transition trigger and owner instead of multiple defensive checks;
- use one monotonic causal ordering authority rather than timestamp heuristics;
- establish durable ownership before an effect when crash recovery requires it;
- preserve the base outcome after successful teardown and use one explicit containment override when teardown cannot be proven;
- keep child/unit outcomes distinct from aggregate rollup;
- record never-started units with their blocking cause;
- fail closed on unknown authority-bearing events;
- add explicit recovery authority rather than privileged cleanup bypasses;
- preserve unresolved history rather than retroactively fabricating certainty;
- derive executable test vectors from each corrected edge.

If the current specification already represents every reachable lifecycle path deterministically, leave it alone.

## OUTPUT

Return `# Requirements Lifecycle Closure Review` with:

- reviewed lifecycle scope and effectful phases;
- proven open lifecycle seams, each with failure cut and competing interpretations;
- race/order gaps;
- teardown/quiescence gaps;
- crash/unresolved/recovery gaps;
- evidence/journal gaps;
- smallest normative corrections;
- deterministic acceptance tests needed;
- neighboring concerns intentionally left to other skills.

End with one:

- `CLEAN` — the completed review scope has deterministic lifecycle, partial-failure, ordering, teardown, unresolved, and recovery semantics for every reachable effectful path inspected;
- `LEAVE ALONE` — suspicious omissions were inspected but the current contract already makes those paths impossible or delegates them to an explicit owner;
- `INSUFFICIENT EVIDENCE` — the lifecycle/effect boundary cannot be established far enough to justify either a finding or a clean claim.
