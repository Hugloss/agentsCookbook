# Skill Catalog

The repository keeps skills deliberately small and sharp. One skill should own one narrow review or discovery question with one hard invariant. Specialist review skills should hunt one failure class.

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
- `repository-improvement-scout` — Find evidence-backed repository signals worth investigating next.
- `codebase-finding-derivation` — Turn inspected code paths into defensible evidence-backed findings.
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

## Data handling

- `sensitive-data-masking` — Produce shareable bounded documents and logs by consistently masking PII, credentials, secrets, and sensitive infrastructure data, with fail-closed verification.

## Evidence integrity

- `semantic-identity-invariance-review` — Find authoritative identities that change on semantic no-ops or ignore semantic changes they claim to cover.
- `evidence-projection-preservation-review` — Find admitted evidence silently erased or hidden by downstream projections.
- `completeness-accounting-review` — Find complete/success claims with expected units left unaccounted.
- `bounded-authority-monotonicity-review` — Find authority that oscillates when only retrieval or presentation bounds change.
- `cache-validity-binding-review` — Find cache keys or validity checks that omit semantic inputs or authority generation.
- `persistence-roundtrip-convergence-review` — Find persisted state that changes semantics or identity across save/reopen/decode.
- `evidence-provenance-binding-review` — Find reusable evidence whose identity omits provenance required for safe interpretation.
- `unknown-state-collapse-review` — Find unknown, missing, incomplete, stale, or invalid state collapsed into ordinary values.
- `cross-surface-convergence-review` — Find semantic or authority divergence across equivalent API, CLI, MCP, compact, report, or persistence surfaces.
- `semantic-noninterference-review` — Find conclusions changed by evidence outside their declared semantic dependency or proof scope.
- `evidence-visibility-enforcement-review` — Find denied or hidden evidence leaking into selection, authority, diagnostics, caches, or public output.

## Semantic authority

- `authority-escalation-review` — Find derived evidence that gains stronger authority without new qualifying proof.
- `semantic-redecision-review` — Find the same semantic answer being independently decided twice.
- `durable-commit-path-review` — Find one durable transition committing through multiple paths.
- `resolved-fact-regression-review` — Find downstream code falling back from resolved facts to raw inputs.
- `state-authority-review` — Find competing representations acting as truth.
- `invalid-state-model-review` — Find impossible domain/lifecycle states that remain representable.

## Qualification integrity

- `aggregate-hard-failure-masking-review` — Find hard contract violations hidden by aggregate scores or unrelated positive measurements.
- `measurement-comparability-review` — Find deltas or rankings computed across incompatible measurement conditions.
- `evidence-readiness-review` — Find qualification claims made before the evidence set is eligible, non-vacuous, and sufficiently representative.
- `baseline-self-authorization-review` — Find changes that weaken their own governing baseline or policy and then validate against that candidate state.

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

- `repository-improvement-scout` asks **what repository signals are worth investigating next**; `codebase-finding-derivation` asks **whether one investigated signal is proven enough to become a finding**; `architecture-risk-triage` asks **which narrow specialist should inspect an evidence-backed architecture hotspot**.
- `codebase-finding-derivation` asks **whether inspected code evidence justifies a finding at all**; `fact-grounding-auditor` asks **whether an existing repository-specific claim is supported**.
- `coverage-design-review` asks **what real behavior is not proved**; `test-contract-coupling-review` asks **what tests freeze private implementation**.
- `code-performance-optimization-audit` asks **where runtime cost scales badly**; `test-work-amplification-review` starts from measured slow tests; `single-observation-review` asks whether one logical operation observes the same input world twice.
- `semantic-redecision-review` catches the same semantic answer being made repeatedly; `resolved-fact-regression-review` catches a resolved answer being discarded so downstream code returns to raw facts.
- `state-authority-review` asks **which representation is truth**; `invalid-state-model-review` asks **whether that representation can express impossible states**.
- `stale-work-race-review` asks whether superseded old work can still commit; `retry-idempotency-review` asks whether the **same logical operation** can repeat a one-shot effect.
- `durable-commit-path-review` asks why one transition has multiple commit authorities; `atomic-operation-review` asks whether one legitimate path can expose only part of its required outcome.
- `resource-lifetime-review` owns general acquire/use/release lifetime; `ui-lifecycle-race-review` owns delayed work specifically outliving a UI/view generation.
- `failure-contract-review` owns failure meaning, retryability, and recovery semantics; `unknown-state-collapse-review` owns loss of uncertainty when no failure contract is being reinterpreted; `semantic-redecision-review` owns broader repeated policy interpretation.
- `state-authority-review` finds competing truth representations; `authority-escalation-review` finds evidence becoming more authoritative while flowing through a layer without new proof.
- `semantic-identity-invariance-review` tests whether identity follows semantics; `persistence-roundtrip-convergence-review` tests whether save/reopen/decode preserves those semantics.
- `evidence-projection-preservation-review` follows individual admitted facts through projections; `completeness-accounting-review` reconciles the whole expected universe.
- `bounded-authority-monotonicity-review` tests authority across retrieval/presentation bounds; `semantic-identity-invariance-review` tests identity across any semantic no-op representation change.
- `evidence-provenance-binding-review` asks whether one reusable evidence artifact binds its authority context; `measurement-comparability-review` asks whether two measurements are valid to compare.
- `evidence-readiness-review` asks whether evidence is sufficient to qualify at all; `aggregate-hard-failure-masking-review` asks whether a hard violation can be compensated after readiness is established.
- `cache-validity-binding-review` owns semantic cache-key/validity completeness; `stale-work-race-review` owns superseded asynchronous work committing after newer ownership exists.
- `cross-surface-convergence-review` compares equivalent public surfaces; `evidence-projection-preservation-review` follows evidence through one projection chain.
- `semantic-noninterference-review` asks whether out-of-scope evidence changes a conclusion; `bounded-authority-monotonicity-review` narrows that question specifically to retrieval/presentation bounds.
- `evidence-visibility-enforcement-review` owns denied/hidden evidence crossing an admission boundary; `evidence-projection-preservation-review` owns admitted evidence disappearing after admission.
- `baseline-self-authorization-review` asks whether a candidate can weaken its own governing oracle; `measurement-comparability-review` asks whether separately produced measurements are comparable once their governing contracts are fixed.
- `call-chain-collapse-review` targets no-value hops; `dependency-surface-review` targets oversized inputs/contexts even when the call depth is reasonable.
- `red-team-leftover-gate` reviews a supplied plan/change for material blockers; `architecture-risk-triage` routes repository hotspots to specialist architecture reviews.

When two skills could notice the same code, report the defect under the skill whose invariant is actually violated.
