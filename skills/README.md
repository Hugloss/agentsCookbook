# Skill Catalog

The repository keeps skills deliberately small and sharp. One skill should hunt one failure class with one hard invariant.

## Skill doctrine

Every skill should:
- trace real production or test paths rather than grep patterns alone;
- prove the defect before reporting it;
- name the main false positives;
- prefer deletion, consolidation, and stronger boundaries over new layers;
- protect coherent owners that do not need refactoring;
- avoid fixed finding quotas.

A strong finding normally removes a path, decision, representation, traversal, branch, wrapper, synchronization mechanism, or source of ambiguity.

## Planning and evidence

- `plan-gap-scout` — Find missing implementation work without rewriting the plan.
- `alternative-route-challenge` — Challenge a plan with a genuinely different evidence-backed route.
- `validation-gap-finder` — Design decisive validation and recovery proof.
- `coverage-design-review` — Check whether tests prove real production behavior.
- `implementation-dry-run` — Simulate implementation to find missing steps and sequencing.
- `fact-grounding-auditor` — Verify repo-specific claims and uncertainty.
- `plan-contract-guard` — Check final handoff completeness and executability.
- `red-team-leftover-gate` — Find material blockers and leftovers before handoff.
- `code-performance-optimization-audit` — Find material runtime scaling and repeated-work cost.

## Concurrency

- `stale-work-race-review` — Find old async work that can commit after newer ownership exists.
- `ui-lifecycle-race-review` — Find delayed UI work that outlives its view or interaction.

## Execution integrity

- `atomic-operation-review` — Find logical operations that can expose partial externally visible state.
- `retry-idempotency-review` — Find replay/retry paths that can repeat one-shot effects.
- `resource-lifetime-review` — Find resources that leak, close too early, or outlive their owner.
- `failure-contract-review` — Find failure meaning or recovery contracts that diverge across layers.

## Semantic authority

- `semantic-redecision-review` — Find the same semantic answer being independently decided twice.
- `durable-commit-path-review` — Find one durable transition committing through multiple paths.
- `resolved-fact-regression-review` — Find downstream code falling back from resolved facts to raw inputs.
- `state-authority-review` — Find competing representations acting as truth.
- `invalid-state-model-review` — Find impossible domain/lifecycle states that remain representable.

## Structural simplicity

- `single-observation-review` — Find one logical operation observing the same input world twice.
- `call-chain-collapse-review` — Find forwarding layers that add no meaningful guarantee.
- `alternate-path-removal-review` — Find obsolete architecture paths beside a canonical one.
- `hidden-side-effect-review` — Find externally visible effects hidden behind misleading boundaries.
- `dependency-surface-review` — Find APIs and contexts that expose far more state than behavior needs.

## Test-derived architecture

- `test-work-amplification-review` — Trace slow tests to disproportionate production work.
- `repeated-test-setup-review` — Find expensive architecture construction repeated across tests.
- `test-isolation-boundary-review` — Find local behavior forced to depend on unrelated effects.
- `test-orchestration-complexity-review` — Find tests exposing too many production responsibilities.
- `deterministic-causality-test-review` — Replace scheduler luck with explicit causal control.
- `test-state-contamination-review` — Find hidden mutable state leaking between tests.
- `test-contract-coupling-review` — Find tests freezing private choreography instead of contracts.

## Discovery

- `architecture-risk-triage` — Route evidence-backed hotspots to the narrow specialist skill.

## Overlap boundaries

Use the narrowest skill that owns the question:

- `coverage-design-review` asks **what real behavior is not proved**; `test-contract-coupling-review` asks **what tests freeze private implementation**.
- `code-performance-optimization-audit` asks **where runtime cost scales badly**; `test-work-amplification-review` starts from measured slow tests; `single-observation-review` asks whether one logical operation observes the same input world twice.
- `semantic-redecision-review` catches the same semantic answer being made repeatedly; `resolved-fact-regression-review` catches a resolved answer being discarded so downstream code returns to raw facts.
- `state-authority-review` asks **which representation is truth**; `invalid-state-model-review` asks **whether that representation can express impossible states**.
- `stale-work-race-review` asks whether superseded old work can still commit; `retry-idempotency-review` asks whether the **same logical operation** can repeat a one-shot effect.
- `durable-commit-path-review` asks why one transition has multiple commit authorities; `atomic-operation-review` asks whether one legitimate path can expose only part of its required outcome.
- `resource-lifetime-review` owns general acquire/use/release lifetime; `ui-lifecycle-race-review` owns delayed work specifically outliving a UI/view generation.
- `failure-contract-review` owns failure meaning, retryability, and recovery semantics; `semantic-redecision-review` owns broader repeated policy interpretation.
- `call-chain-collapse-review` targets no-value hops; `dependency-surface-review` targets oversized inputs/contexts even when the call depth is reasonable.
- `red-team-leftover-gate` reviews a supplied plan/change for material blockers; `architecture-risk-triage` routes repository hotspots to specialist architecture reviews.

When two skills could notice the same code, report the defect under the skill whose invariant is actually violated.
