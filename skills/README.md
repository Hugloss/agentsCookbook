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
- `shared-state-ownership-review` — Find race or synchronization reasoning that misclassifies whether mutable state is actually shared.

## Execution integrity

- `atomic-operation-review` — Find logical operations that can expose partial externally visible state.
- `retry-idempotency-review` — Find replay/retry paths that can repeat one-shot effects.
- `resource-lifetime-review` — Find resources that leak, close too early, or outlive their owner.
- `failure-contract-review` — Find failure meaning or recovery contracts that diverge across layers.
- `dogfood-saturation-loop` — Drive one repair surface through repeated post-patch dogfood until fresh probing yields no qualifying defect.

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
- `explicit-target-resolution-review` — Find explicit paths or symbols displaced by weaker inferred candidates without conflating intent with ownership.
- `roundtrip-capacity-contract-review` — Find valid payloads that cannot traverse documented downstream or round-trip paths because layer bounds disagree.
- `evidence-integrity-revalidation-review` — Find reusable evidence identities trusted without recomputing them from current content.
- `identifier-scope-uniqueness-review` — Find identifiers used as identity outside the scope where uniqueness is guaranteed.
- `negative-evidence-admissibility-review` — Find absence claims treated as evidence without complete non-truncated observation scope.
- `orthogonal-state-axis-review` — Find independent semantic dimensions collapsed into one status, enum, or flag.
- `stable-observation-snapshot-review` — Find one logical observation assembled from incompatible revisions or generations.
- `static-evidence-overclaim-review` — Find static analyzers claiming exact facts beyond what their resolution model proves.
- `path-scope-confinement-review` — Find path normalization, mapping, symlink, or locator logic that can escape its declared authority root.

## Semantic authority

- `authority-escalation-review` — Find derived evidence that gains stronger authority without new qualifying proof.
- `semantic-redecision-review` — Find the same semantic answer being independently decided twice.
- `durable-commit-path-review` — Find one durable transition committing through multiple paths.
- `resolved-fact-regression-review` — Find downstream code falling back from resolved facts to raw inputs.
- `state-authority-review` — Find competing representations acting as truth.
- `invalid-state-model-review` — Find impossible domain/lifecycle states that remain representable.
- `correlation-causation-boundary-review` — Find correlation promoted into causation, incident identity, responsibility, or remediation authority.

## Qualification integrity

- `aggregate-hard-failure-masking-review` — Find hard contract violations hidden by aggregate scores or unrelated positive measurements.
- `measurement-comparability-review` — Find deltas or rankings computed across incompatible measurement conditions.
- `evidence-readiness-review` — Find qualification claims made before the evidence set is eligible, non-vacuous, and sufficiently representative.
- `baseline-self-authorization-review` — Find changes that weaken their own governing baseline or policy and then validate against that candidate state.
- `current-measurement-authority-review` — Find historical baselines or snapshots reused as if they measured current state.
- `improvement-claim-remeasurement-review` — Find improvement claims inferred from code movement instead of comparable post-change measurement.

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
- `verification-locality-review` — Find generic-ranked verification displacing stronger target-bound or reference-backed verification.

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
- `current-measurement-authority-review` asks **what measures current state**; `baseline-self-authorization-review` asks **whether the governing baseline itself can be weakened by the candidate**.
- `improvement-claim-remeasurement-review` asks **whether the claimed improvement actually occurred**; `measurement-comparability-review` asks **whether the before/after measurements are valid to compare**.
- `roundtrip-capacity-contract-review` owns incompatible bounds across composition paths; `completeness-accounting-review` owns whether all expected units inside one admitted scope were accounted for.
- `evidence-integrity-revalidation-review` verifies that reusable content still matches its claimed identity; `evidence-provenance-binding-review` verifies that the identity binds the authority context needed to interpret it.
- `identifier-scope-uniqueness-review` asks whether an identifier is unique where it is used; `semantic-identity-invariance-review` asks whether a canonical identity changes exactly with semantics.
- `negative-evidence-admissibility-review` owns whether absence can be used as evidence; `unknown-state-collapse-review` owns whether unknown/incomplete state is collapsed into an ordinary value.
- `orthogonal-state-axis-review` asks whether independent semantic dimensions are modeled separately; `invalid-state-model-review` asks whether the resulting state model can represent impossible domain states.
- `stable-observation-snapshot-review` asks whether one logical observation comes from one coherent source state; `single-observation-review` asks whether one operation redundantly observes the same world multiple times.
- `static-evidence-overclaim-review` owns analyzers claiming more certainty than their proof model permits; `authority-escalation-review` owns downstream layers strengthening already-produced evidence without new proof.
- `path-scope-confinement-review` owns path/locator escape across repository, workspace, tenant, or analysis roots; `evidence-visibility-enforcement-review` owns already-admitted evidence crossing visibility policy boundaries.
- `correlation-causation-boundary-review` owns correlation being promoted into causal or remediation claims; `authority-escalation-review` owns broader evidence-to-authority strengthening.
- `explicit-target-resolution-review` owns preservation of uniquely resolved request targets; `authority-escalation-review` owns any stronger authority later minted from those targets without proof.
- `verification-locality-review` asks which existing evidence best verifies the target behavior; `coverage-design-review` asks what behavior is not proved at all.
- `shared-state-ownership-review` asks whether mutable state is actually shared; `stale-work-race-review` asks whether superseded work can commit after newer ownership exists.
- `call-chain-collapse-review` targets no-value hops; `dependency-surface-review` targets oversized inputs/contexts even when the call depth is reasonable.
- `red-team-leftover-gate` reviews a supplied plan/change for material blockers; `architecture-risk-triage` routes repository hotspots to specialist architecture reviews.
- `dogfood-saturation-loop` governs **when a repair campaign may stop and when broad validation should run**; it consumes evidence-backed defect proof from `codebase-finding-derivation` or a narrow specialist rather than promoting investigation leads itself. `repository-improvement-scout` finds leads and `verification-locality-review` selects the strongest verifier. The loop consumes repository qualification authority for closure; `baseline-self-authorization-review` owns whether the candidate improperly weakens that authority.

When two skills could notice the same code, report the defect under the skill whose invariant is actually violated.
