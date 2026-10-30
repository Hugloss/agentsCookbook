# AgentsCookbook skill quality review — 2026-10-30

## Outcome and evidence boundary

Reviewed every one of the **84 existing skill definitions** at [baseline `1698ba20e240`](https://github.com/Hugloss/agentsCookbook/tree/1698ba20e240b2b4eb8e21a4c6bf2827ad882725), including the Kafka, pytest and event-observation references. **68 existing definitions were sharpened, 16 were retained unchanged, and one distinct skill was extracted**, giving a catalog of **85**.

The catalog was not uniformly precise. The most consequential defects were inconsistent result contracts, insufficiently bounded negative conclusions, missing safe-case controls, and instructions that could make an agent invent facts or recommend unnecessary work. Many compact skills needed only a few targeted sentences; they did not need the length of the Kafka skill.

These are **definition-level review and improvement results**, not accuracy scores or production certification. A retained skill means no material definition defect was established in this review. A revised skill means a concrete decision boundary was strengthened, not that it was previously useless. No numerical reduction in hallucinations, model/provider parity, or production reliability is claimed.

This document is an audit record, not a second skill registry or a new runtime gate. Canonical discovery remains `skills/*/SKILL.md`; the catalog and existing nine-reviewer flow retain their ownership.

## What “platinum” requires in practice

Use the word as a reliability goal. Judge a skill by the decisions it helps an agent make:

1. **Select the right job.** Its name and description distinguish the intended task from neighboring skills before the full body loads.
2. **Establish facts before deciding.** Required contracts, source paths, dependency versions, API semantics and evidence must be inspected or explicitly unresolved.
3. **Prove the failure.** A plausible smell or missing test does not become a product defect without a reachable violation and consequence.
4. **Protect valid cases.** A near-neighbor control shows why supported compatibility, legitimate fresh reads, existing idempotency or an intentional validation boundary should remain.
5. **Preserve uncertainty.** Incomplete inspection cannot support a clean conclusion; a proved finding must remain visible alongside other unknowns.
6. **Verify the claimed result.** Definition review, a representative agent application, formal behavioral evaluation, and execution of generated code establish different things.
7. **Keep the useful boundary small.** Split independently useful decisions; keep dependent checks together when one end-to-end guarantee needs them all. Optional examples and variants can live in references.

No fixed prompt length, number of skills, benchmark score, or passing structural check substitutes for those properties.

## Material findings and corrections

### Proved findings had no truthful final verdict

Five definitions could establish a defect but their exhaustive terminal result lists offered only clean, leave-alone and insufficient-evidence outcomes:

- [proxy-gate-authority-review](../skills/proxy-gate-authority-review/SKILL.md)
- [requirements-lifecycle-closure-review](../skills/requirements-lifecycle-closure-review/SKILL.md)
- [native-tool-authority-review](../skills/native-tool-authority-review/SKILL.md)
- [entrypoint-authority-review](../skills/entrypoint-authority-review/SKILL.md)
- [hidden-authority-cucumber-attack](../skills/hidden-authority-cucumber-attack/SKILL.md)

Each now permits an explicit `FINDING` and retains unresolved neighboring scope. The older result lists are available in the pinned baseline. The fresh quality-checker application independently identified this contradiction in the baseline proxy-gate definition.

### Clean conclusions and missing evidence were not consistently bounded

Several small specialist definitions described findings but never specified what an empty report meant. Older planning skills allowed “None” or “complete” without stating which obligations and dependencies had to be inspected. The revisions bind absence to the skill's actual question, preserve unknown evidence, and distinguish a completed plan or source review from successful execution.

The planning changes also protect normal implementation freedom and intentional creation. Independent review found that an initial edit incorrectly treated every nonexistent target as a defect. The corrected rule reports only a prerequisite that must already exist; a planned new file is legitimate when its creation, parent, owner and prerequisites are accounted for.

### Hunt patterns could become false alarms

Examples of strengthened controls include:

| Skill or group | Decision now made explicitly |
| --- | --- |
| Invalid state models | A raw transport object may represent invalid input safely when one canonical admission boundary rejects it before trusted use. |
| Cache validity | Inspect the key, invalidation and read-time validity together; an omitted key field alone is not a defect. |
| Evidence integrity | Already verified immutable ownership can justify reuse without redundant hashes at every consumer. |
| Cross-surface convergence | Compare equivalent authorization, visibility, configuration and API contracts before requiring equal results. |
| Repeated observation | Preserve intentional fresh reads and independent trust verification. |
| Compatibility removal | Lack of local callers or an old name does not establish that external support obligations have ended. |
| Shared-state ownership | A shallow copy can share nested objects; a lock protecting a local map may also protect a shared durable effect. |
| Test design | Preserve required integration behavior, effective reset fixtures and actual behavioral detection when simplifying tests. |
| Measurement comparability | The intended experimental treatment is allowed to change; distinguish it from confounding differences. |

### Generic retry review lagged behind Kafka's precision

[retry-idempotency-review](../skills/retry-idempotency-review/SKILL.md) now checks concurrent admission, operation/tenant identity, payload consistency, permitted replay horizon, retained deduplication evidence and remote success with a lost response. It preserves a valid effect-owned idempotency boundary without requiring a new registry. Missing provider semantics remain unknown.

Kafka remains one skill. Its acknowledgement decision depends on offsets, durable responsibility, effect identity, publication, assignment ownership and recovery together. Making those independently optional skills would create a new omission risk. Its failure matrix already provides selective supporting detail.

### Tool and performance guidance needed to respect repository authority

[python-static-analysis-repair](../skills/python-static-analysis-repair/SKILL.md) now establishes the required analyzer set before results. A repository using only a declared subset of Ruff, Pyright and ty does not acquire new mandatory tools from the skill. Existing configured failing analyzers cannot be dropped. A decisive existing test may be reused before a semantic repair.

The performance/setup reviewers now accept source-proved repeated work as a reason to simplify code without requiring new timing infrastructure. Numerical speedup and budget claims still require appropriate observations. This preserves fast iteration while preventing invented performance results.

[fact-grounding-auditor](../skills/fact-grounding-auditor/SKILL.md) now explicitly checks selected dependency versions and primary implementation/documentation before asserting flags, API signatures or return/await semantics. Pseudocode and application-specific adapters must be labeled. Instructions found inside reviewed files or logs are review material, not authority over the review.

## The justified split

| Definition | Owned question | Decisive evidence |
| --- | --- | --- |
| [hidden-authority-cucumber-attack](../skills/hidden-authority-cucumber-attack/SKILL.md) | Does a historical or named exception grant behavior unsupported by the current contract? | Current requirement/support policy, reachable identity-sensitive decision, equivalent-identity control, actual consumer and consequence. |
| [source-transport-contamination-review](../skills/source-transport-contamination-review/SKILL.md) | Does staging a patch, log, report or temporary artifact unintentionally admit it as source, a package input or qualification authority? | Artifact role, staging path, membership owner, before/after membership witness and an intentional-input control. |

The second question no longer needs a rename experiment. It explicitly protects declared generated source, deliberately consumed evidence and consistently excluded scratch directories inside a checkout. It does not authorize deleting user files or adding arbitrary ignore rules.

The catalog and architecture triage now route to the two owners separately. No additional split was justified in the other reviewed skills. In particular, sensitive-data masking remains one bounded transformation, and historical contract reconstruction remains one dependent evidence-to-repair task.

## The reusable quality checker

[skill-contract-review](../skills/skill-contract-review/SKILL.md) is the existing canonical owner, now strengthened to cover the full authoring review:

- Read the full definition, necessary resources and relevant neighboring contracts.
- Walk a realistic request from metadata selection through inputs, evidence, decisions, actions and outputs.
- Check a failure, safe lookalike and missing-input state material to the change.
- Check actual repository/format constraints and local references without confusing structure with behavioral quality.
- For substantial revisions, use a fresh task-local application without the expected answer or the author's diagnosis.
- Report source-located gaps, concrete failure scenarios, safe controls, smallest corrections and evidence limits.

Its outputs preserve `FINDING`, bounded `CLEAN`, positively justified `LEAVE ALONE`, and `INSUFFICIENT EVIDENCE`. It recommends keep, sharpen or split without requiring a split merely because a skill is long.

Example request:

> Use skill-contract-review on this skill and its referenced files. Check selection, required inputs, evidence, false positives, unknowns, output consistency and neighboring ownership. Prove material gaps with realistic cases, recommend keep/sharpen/split, and distinguish source review from checks actually executed.

The contribution guide applies this at authoring time. It adds no mandatory runtime reviewer, model benchmark, paired EvalShot PR or new framework. Formal reusable evaluation assets still belong to EvalShot when that work is needed.

## Validation

| Evidence | Result and limit |
| --- | --- |
| Complete catalog read | All 84 baseline definitions, applicable linked references and overlap boundaries inspected; the new split reviewed too. |
| Independent definition review | Cross-review of the proposed changes completed. The planned-file false-positive was found, corrected and independently rechecked. No further material definition gap was established in the completed scope. |
| Fresh application of the quality checker | Three supplied drafts: baseline proxy verdict contradiction found; a valid finite-object reviewer retained; unavailable organizational policy/neighbors kept unresolved without inventing a defect. |
| Fresh applications of revised specialists | Nine bounded path/model judgments across packaging, state admission and retry scenarios; findings, legitimate controls and unavailable provider semantics were distinguished. Source-only: no target implementation executed. |
| Canonical source checks | PASS; 85 skills, 12 agents, 2 adapters, 9 mandatory flow reviewers. |
| OpenCode script smoke suite | PASS. This does not qualify live model/host behavior. |
| Run-artifact smoke suite | PASS. This checks artifact contracts, not skill accuracy. |
| Skill metadata and linked resources | Matching names, descriptions within repository limits, license metadata preserved, and local resources present. |
| Whitespace/diff check | PASS. |
| Formal before/after model evaluation | NOT RUN. No measured accuracy or hallucination-reduction claim. |
| Live Kafka/PostgreSQL/service or generated implementation execution | NOT RUN. No runtime reliability or performance claim. |

The representative tasks are authoring exercises, not a new durable benchmark corpus or a statistically representative evaluation. The existing smoke suites were reused; no wording-matching tests were added.

### Representative application outcomes

Fresh task-local agents received the revised skill and raw case material without the expected answer or the prior review diagnosis. The following decisions were inspected after completion:

| Supplied case | Observed bounded decision |
| --- | --- |
| Baseline proxy-gate skill with a proof procedure but no finding verdict | `FINDING`: output contradiction identified. |
| Complete small required-field reviewer with explicit false/null/zero and unknown controls | `LEAVE ALONE`: no extra runtime or provenance machinery demanded. |
| Policy-driven publication reviewer without the organization's policy or neighbors | `INSUFFICIENT EVIDENCE` for organizational fit; missing context was not fabricated into a definition defect. |
| Diagnostic Python helper staged under a package's recursive source glob | `FINDING`: source-only before/after membership witness, with intended edits held constant. |
| Declared tracked generator output | `LEAVE ALONE`: intentional input preserved. |
| Diagnostic helper in an explicitly excluded in-tree scratch directory | `LEAVE ALONE`: location alone did not establish contamination. |
| Legacy command explicitly supported for external clients | `LEAVE ALONE`: current compatibility contract preserved. |
| Raw state DTO followed by canonical validated admission | `LEAVE ALONE`: language-level representability did not become an admitted-state defect. |
| Request admitted as completed state with no result and no validation | `FINDING`: reachable invalid state and consumer failure traced. |
| Separate ledger read, remote debit and ledger mark | `FINDING`: concurrent retry and debit-success/response-loss sequences traced. |
| Effect owner with atomic tenant/operation idempotency and adequate retention | `LEAVE ALONE`: no extra deduplication registry demanded. |
| Forwarded request identity with unavailable provider semantics | `INSUFFICIENT EVIDENCE`: neither duplicate effect nor safety invented. |

The service and policy contracts were supplied scenario inputs, not independently verified live implementations. These outcomes are useful evidence that the revised instructions can be applied to the intended distinctions; they do not quantify a before/after accuracy change or coverage of all 85 skills.

## Per-skill disposition

The table covers every current catalog definition exactly once. **Retained** means no material definition change was justified in the bounded static review. **Revised** includes narrow outcome clarification as well as domain corrections. **Split/new** records the extracted independent question. None is a model-quality grade.

### Skill authoring

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [skill-contract-review](../skills/skill-contract-review/SKILL.md) | Revised | Expanded the reusable authoring check to selection, complete input review, verified API examples, output consistency, justified splitting and independent representative application; no universal certification. |

### Change review

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [source-change-review](../skills/source-change-review/SKILL.md) | Retained | Requirement authority, base/candidate attribution, affected-path expansion, disconfirmation, evidence limits and all four verdicts are already explicit. |
| [test-removal-review](../skills/test-removal-review/SKILL.md) | Retained | Separates active obligations, old-test validity, replacement protection, escaped failures and actual product defects; supports scoped clean and unknown outcomes. |

### Planning and evidence

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [plan-gap-scout](../skills/plan-gap-scout/SKILL.md) | Revised | Bound no-gap claims to established obligations and inspected callers; distinguish absent work from unavailable evidence and protect valid existing ownership. |
| [alternative-route-challenge](../skills/alternative-route-challenge/SKILL.md) | Retained | Already requires a materially different evidence-backed route, preserves tradeoffs and bounded no-better-route/unknown outcomes. |
| [validation-gap-finder](../skills/validation-gap-finder/SKILL.md) | Retained | Already establishes obligations independently of passing checks, verifies policy authority and separates proposed or skipped validation from completed evidence. |
| [coverage-design-review](../skills/coverage-design-review/SKILL.md) | Revised | A coverage gap needs an inspected missed-detection witness and real obligation; protect coverage at other test levels and separate hypothetical broken code from a current product defect. |
| [implementation-dry-run](../skills/implementation-dry-run/SKILL.md) | Revised | Bound the simulated sequence, forbid invented prerequisites/APIs, preserve ordinary implementation freedom and planned file creation, and distinguish simulation from execution. |
| [fact-grounding-auditor](../skills/fact-grounding-auditor/SKILL.md) | Revised | Inventory claims, revisions and source support; verify version-sensitive APIs/flags; distinguish contradiction, assumption, missing evidence and executed results. |
| [repository-improvement-scout](../skills/repository-improvement-scout/SKILL.md) | Retained | Already separates signals and leads from proved findings, requires a real path and disconfirmation, and bounds no-more-leads to completed inspection. |
| [codebase-finding-derivation](../skills/codebase-finding-derivation/SKILL.md) | Retained | Already requires path, expectation, violation, consequence, evidence and disconfirmation, with complete-scope bounds on absence. |
| [plan-contract-guard](../skills/plan-contract-guard/SKILL.md) | Revised | Establish requested obligations before handoff judgment; protect valid references/irrelevant checklist items and distinguish complete plan from completed implementation. |
| [red-team-leftover-gate](../skills/red-team-leftover-gate/SKILL.md) | Revised | Keep proved blockers visible alongside unresolved scope instead of replacing every non-clean outcome with insufficient evidence. |
| [code-performance-optimization-audit](../skills/code-performance-optimization-audit/SKILL.md) | Revised | Allow source-proved work reduction without timing infrastructure; account for real workload and safe caching/isolation controls; no numerical speedup without observation. |

### Concurrency

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [stale-work-race-review](../skills/stale-work-race-review/SKILL.md) | Revised | Old output mixed confirmed and potential races without a finding threshold or bounded negative result; pre-effect checks and cancellation could be treated as sufficient despite later ownership change. |
| [ui-lifecycle-race-review](../skills/ui-lifecycle-race-review/SKILL.md) | Revised | Replacement sequence alone did not require an observable wrong effect; output mixed potential and confirmed races and did not preserve missing framework/cleanup semantics. |
| [shared-state-ownership-review](../skills/shared-state-ownership-review/SKILL.md) | Revised | Fresh/local language could justify lock removal without tracing shallow aliases, external identities, or other effects protected by the same critical section. |

### Execution integrity

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [kafka-delivery-safety-review](../skills/kafka-delivery-safety-review/SKILL.md) | Retained | Definition and failure matrix already bind delivery, effect, ordering and recovery guarantees to scope, client/version, actual settlement, safe controls and qualification limits. |
| [atomic-operation-review](../skills/atomic-operation-review/SKILL.md) | Revised | Finding proof did not explicitly establish governing atomic/staged contract or visibility before compensation; no bounded negative/unknown outcome. |
| [retry-idempotency-review](../skills/retry-idempotency-review/SKILL.md) | Revised | Generic proof omitted concurrent admission, identity scope/payload consistency, deduplication lifetime, and ambiguous remote success now explicit in Kafka. |
| [resource-lifetime-review](../skills/resource-lifetime-review/SKILL.md) | Revised | Ownership ambiguity could be reported without concrete consequence; partial acquisition, cancellation of cleanup, escaped borrowers and external stopping needed sharper evidence. |
| [failure-contract-review](../skills/failure-contract-review/SKILL.md) | Revised | Failure-name/retry interpretation lacked explicit operation-outcome distinction and requirement authority; missing semantics could become invented policy. |
| [requirements-lifecycle-closure-review](../skills/requirements-lifecycle-closure-review/SKILL.md) | Revised | Skill defines findings but its terminal output omitted FINDING; clean applied only to paths inspected without requiring completion of a declared material lifecycle scope. |
| [dogfood-saturation-loop](../skills/dogfood-saturation-loop/SKILL.md) | Retained | Already binds current candidate, authoritative scope, fresh complete probes and independent final qualification; keeps skipped/failing work incomplete. |
| [adversarial-repair-campaign](../skills/adversarial-repair-campaign/SKILL.md) | Retained | Already owns the feedback loop and current candidate without pretending to be every defect oracle or final qualification owner. |
| [python-static-analysis-repair](../skills/python-static-analysis-repair/SKILL.md) | Revised | Use the pre-established repository analyzer set instead of mandating all three tools; reuse decisive existing tests while preserving pre-change behavior protection. |

### Data handling

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [sensitive-data-masking](../skills/sensitive-data-masking/SKILL.md) | Retained | Already distinguishes disclosure policy from detection, preserves diagnostic meaning, rechecks transformed content, and keeps uninspected or unresolved content incomplete. |

### Evidence integrity

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [semantic-identity-invariance-review](../skills/semantic-identity-invariance-review/SKILL.md) | Revised | Output asks only for findings and does not bound absence to the inspected identity contracts and transformations. |
| [evidence-projection-preservation-review](../skills/evidence-projection-preservation-review/SKILL.md) | Revised | No bounded negative outcome; preservation advice could expose evidence a later visibility boundary legitimately withholds. |
| [completeness-accounting-review](../skills/completeness-accounting-review/SKILL.md) | Revised | No negative outcome; expected universe lacks independent authority and complete accounting could be mistaken for successful work. |
| [bounded-authority-monotonicity-review](../skills/bounded-authority-monotonicity-review/SKILL.md) | Revised | No negative outcome or explicit unknown handling when the cause of authority changes cannot be established. |
| [cache-validity-binding-review](../skills/cache-validity-binding-review/SKILL.md) | Revised | Proof wording can condemn a dimension missing from the key even when invalidation or read-time validity safely binds it; no bounded outcome. |
| [persistence-roundtrip-convergence-review](../skills/persistence-roundtrip-convergence-review/SKILL.md) | Revised | No bounded clean/unknown outcome; traced and executed roundtrip evidence not distinguished. |
| [evidence-provenance-binding-review](../skills/evidence-provenance-binding-review/SKILL.md) | Revised | No bounded absence/unknown outcome despite reuse-context dependent proof. |
| [unknown-state-collapse-review](../skills/unknown-state-collapse-review/SKILL.md) | Revised | No explicit outcome for an unknown domain equivalence or completed bounded review. |
| [cross-surface-convergence-review](../skills/cross-surface-convergence-review/SKILL.md) | Revised | Same source/generation alone does not establish surface equivalence across permissions, policy, configuration, or API contracts; no bounded outcome. |
| [semantic-noninterference-review](../skills/semantic-noninterference-review/SKILL.md) | Revised | Scope can be assumed rather than established; removing redundant in-scope evidence need not change an answer, and no bounded outcome exists. |
| [evidence-visibility-enforcement-review](../skills/evidence-visibility-enforcement-review/SKILL.md) | Revised | Advice to filter once at earliest boundary can miss later policy/caller changes; no bounded outcome. |
| [explicit-target-resolution-review](../skills/explicit-target-resolution-review/SKILL.md) | Revised | No bounded no-finding or ambiguous-resolution outcome. |
| [roundtrip-capacity-contract-review](../skills/roundtrip-capacity-contract-review/SKILL.md) | Revised | Largest/densest payload is not always necessary or well-defined; byte/character/encoded-size mismatches are implicit; no bounded outcome. |
| [evidence-integrity-revalidation-review](../skills/evidence-integrity-revalidation-review/SKILL.md) | Revised | Mandatory recomputation at every reuse boundary can reject safe verified immutable storage/transport ownership and cause waste; no bounded outcome. |
| [identifier-scope-uniqueness-review](../skills/identifier-scope-uniqueness-review/SKILL.md) | Revised | No bounded no-finding/unknown outcome for uninspected producers and uniqueness guarantees. |
| [negative-evidence-admissibility-review](../skills/negative-evidence-admissibility-review/SKILL.md) | Revised | Skill requires complete absence evidence from targets but does not apply that rule to its own negative conclusion. |
| [orthogonal-state-axis-review](../skills/orthogonal-state-axis-review/SKILL.md) | Revised | Safe exhaustive composite encodings are not explicitly protected unless axes are truly coupled; no bounded outcome. |
| [stable-observation-snapshot-review](../skills/stable-observation-snapshot-review/SKILL.md) | Revised | No bounded absence/unknown outcome for snapshot or writer semantics. |
| [static-evidence-overclaim-review](../skills/static-evidence-overclaim-review/SKILL.md) | Revised | No explicit bounded outcome, enabling a sample review to be overread as general analyzer soundness. |
| [path-scope-confinement-review](../skills/path-scope-confinement-review/SKILL.md) | Revised | Confinement stops at normalization/realpath without access-time path replacement and component-boundary checks; no bounded outcome. |

### Semantic authority

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [authority-escalation-review](../skills/authority-escalation-review/SKILL.md) | Revised | Proof did not require the governing stronger-claim contract or distinguish unavailable upstream proof from absent proof; no bounded clean/unknown outcome. |
| [semantic-redecision-review](../skills/semantic-redecision-review/SKILL.md) | Retained | Already distinguishes repeated interpretation from competing accepted authority and backward resolved-fact flow; requires real consequence and bounded outcomes. |
| [known-good-contract-reconstruction](../skills/known-good-contract-reconstruction/SKILL.md) | Revised | LEAVE ALONE allowed no justified repair without distinguishing incomplete baseline evidence. Historical recovery and supported-shape repair otherwise share one coherent contract. |
| [canonical-consumer-contract-review](../skills/canonical-consumer-contract-review/SKILL.md) | Retained | Strong paired counterfactual for the same fact, unknown/ambiguous controls, affected consumer trace and bounded clean scope. |
| [single-source-of-truth-review](../skills/single-source-of-truth-review/SKILL.md) | Retained | Requires competing accepted authority for the same fact/scope/generation, real accepting paths, material consequence and explicit neighboring routing. |
| [durable-commit-path-review](../skills/durable-commit-path-review/SKILL.md) | Revised | Duplicate commit sites could be confused with duplicate semantic authority; shared DB guards and declared transition scope were insufficiently explicit. |
| [resolved-fact-regression-review](../skills/resolved-fact-regression-review/SKILL.md) | Retained | Requires an available resolved result, a real backward boundary, raw-input reinterpretation of the same fact and a consequence; includes controls and scope. |
| [state-authority-review](../skills/state-authority-review/SKILL.md) | Revised | Potentially equated replicated/concurrent representations with competing truth without checking the governing consistency/merge rule; no explicit incomplete outcome. |
| [invalid-state-model-review](../skills/invalid-state-model-review/SKILL.md) | Revised | Language-level representability could be reported even when a canonical validator rejects invalid input before trusted use. |
| [correlation-causation-boundary-review](../skills/correlation-causation-boundary-review/SKILL.md) | Revised | No clear protection for intentionally correlation-based non-causal grouping; absent causal proof could be inferred from unavailable adjudication. |
| [hidden-authority-cucumber-attack](../skills/hidden-authority-cucumber-attack/SKILL.md) | Revised/split | Two independent review jobs: identity-sensitive privilege and incidental artifact staging into source membership. Their witnesses, controls and repairs differ. Also no FINDING final verdict. |
| [source-transport-contamination-review](../skills/source-transport-contamination-review/SKILL.md) | Split/new | New focused owner extracted from the old hidden-authority definition. |

### Qualification integrity

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [empirical-benchmark-campaign](../skills/empirical-benchmark-campaign/SKILL.md) | Revised | Make mechanism-specific preflight checks conditional on frozen experiment contracts and map actual native status labels instead of inventing a harness interface. |
| [aggregate-hard-failure-masking-review](../skills/aggregate-hard-failure-masking-review/SKILL.md) | Revised | Hard requirement authority is assumed in proof; no bounded outcome. |
| [measurement-comparability-review](../skills/measurement-comparability-review/SKILL.md) | Revised | Literal equality of tool/environment/configuration can reject the intended independent variable of a valid comparison; no bounded outcome. |
| [evidence-readiness-review](../skills/evidence-readiness-review/SKILL.md) | Revised | Strong independent qualification authority already exists, but no explicit bounded no-finding/unknown output contract. |
| [proxy-gate-authority-review](../skills/proxy-gate-authority-review/SKILL.md) | Revised | Output excludes FINDING even when PROVE establishes a defect; CLEAN says every inspected gate, permitting a partially inspected declared scope. |
| [baseline-self-authorization-review](../skills/baseline-self-authorization-review/SKILL.md) | Revised | No outcome for unavailable prior governing authority or independent approval. |
| [current-measurement-authority-review](../skills/current-measurement-authority-review/SKILL.md) | Revised | Proof demands an observed different result even when unsupported freshness itself is a demonstrable authority defect; no bounded outcome. |
| [improvement-claim-remeasurement-review](../skills/improvement-claim-remeasurement-review/SKILL.md) | Revised | Unqualified measurement language can turn direct structural simplification into a timing/benchmark requirement; no distinction between missing evidence and measured failure. |

### Structural simplicity

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [single-observation-review](../skills/single-observation-review/SKILL.md) | Revised | Could flag deliberately fresh reads, trust revalidation or chunked observations; repeat API calls alone did not prove equivalent scope/freshness. |
| [call-chain-collapse-review](../skills/call-chain-collapse-review/SKILL.md) | Revised | Hop classification did not explicitly require inspection of dynamic registration, supported public callers, error/cancellation or substitution obligations. |
| [native-tool-authority-review](../skills/native-tool-authority-review/SKILL.md) | Revised | A proven defect could not end in FINDING; assumed native behavior lacked explicit tool/version/config authority verification. |
| [entrypoint-authority-review](../skills/entrypoint-authority-review/SKILL.md) | Revised | Proven duplicate launch ownership had no FINDING final outcome; clean scope could imply all supported entrypoints without an explicit inspected boundary. |
| [alternate-path-removal-review](../skills/alternate-path-removal-review/SKILL.md) | Revised | Legacy/canonical vocabulary could encourage deleting currently supported external compatibility or rollback paths; no-local-callers absence was not bounded. |
| [hidden-side-effect-review](../skills/hidden-side-effect-review/SKILL.md) | Revised | Finding proof was already concrete, but no explicit scope/completeness or unknown outcome prevented unsupported clean/purity claims. |
| [dependency-surface-review](../skills/dependency-surface-review/SKILL.md) | Revised | Large field counts or one caller consuming a subset could be overinterpreted; dynamic/lazy/extension dependencies were not explicitly checked. |

### Integration test construction

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [pytest-hybrid-service-fixtures](../skills/pytest-hybrid-service-fixtures/SKILL.md) | Retained | Main definition and Postgres/Kafka reference explicitly cover service mode, ownership, isolation/reset, async loops, partial startup, actual APIs and unverified environments; direct optimization requires no profiling. |
| [event-driven-test-verification](../skills/event-driven-test-verification/SKILL.md) | Retained | Definition and Kafka/polling reference cover observation arming, replay, correlation, shared readers, production terminal semantics, budgets, cancellation and separate runtime evidence. |

### Test-derived architecture

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [test-work-amplification-review](../skills/test-work-amplification-review/SKILL.md) | Revised | Measure slow tests and remeasure language required measurement before direct optimization; output required measured results even when source proves avoidable work. |
| [repeated-test-setup-review](../skills/repeated-test-setup-review/SKILL.md) | Revised | Measured setup/remeasurement outputs were mandatory; safe reuse proof did not explicitly distinguish infrastructure, schema, mutable data, worker lifetime and live clients. |
| [test-isolation-boundary-review](../skills/test-isolation-boundary-review/SKILL.md) | Revised | Pure/local boundary finding needed established behavior and a traced forced dependency; negative/unknown outputs and preservation of integration assertions were unspecified. |
| [test-orchestration-complexity-review](../skills/test-orchestration-complexity-review/SKILL.md) | Revised | Excessive/too-many language allowed subjective count-based findings without a concrete unnecessary responsibility and consequence. |
| [deterministic-causality-test-review](../skills/deterministic-causality-test-review/SKILL.md) | Revised | Required causal sequence and timing-smell output did not require a supported ordering producing wrong result or unnecessary wait; no clear distinction between executed and reasoned evidence. |
| [test-state-contamination-review](../skills/test-state-contamination-review/SKILL.md) | Revised | Hunt could promote legitimate global reset fixtures into defects, and proof focused on production state while test-support globals also contaminate. |
| [test-contract-coupling-review](../skills/test-contract-coupling-review/SKILL.md) | Revised | Replacement guidance allowed deletion of incidental assertions without explicit preservation of their valid behavioral protection; counterexample and unknown obligation needed explicit treatment. |
| [verification-locality-review](../skills/verification-locality-review/SKILL.md) | Revised | Reference and namespace strength could be mistaken for behavioral coverage without reading actual assertions/discovery/conditions; no bounded unknown verdict. |

### Discovery

| Skill | Disposition | Reason / correction |
| --- | --- | --- |
| [architecture-risk-triage](../skills/architecture-risk-triage/SKILL.md) | Revised | Existing triage correctly separated routing from completed repository-wide review; one old routing destination combined identity and contamination. |

## Remaining evidence work

To claim measured behavioral improvement, use representative positive, safe-control, missing-evidence and competing-skill cases for the decisions being promoted, with fixed candidate identity and a suitable before/after comparison. Test across the models/hosts for which the claim is intended. Construction skills also need execution evidence for the implementations they produce.

That work should be selected for the actual claim, not imposed on every small edit. Until it exists, these changes can be described as reviewed prompt-contract improvements with bounded application evidence. They cannot honestly be described as a guarantee that every agent will make the correct decision.
