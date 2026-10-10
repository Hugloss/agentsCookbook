# Harbor cross-harness repository-intelligence matrix

This directory is an **execution projection**, not a second benchmark authority.

The canonical repository task, pinned repository commit/tree, prompt, mutation,
and oracle remain owned by the referenced agentsCookbook suite. The bridge
projects both bounded read-only `repository-location-json` tasks and frozen
behavioral command-oracle tasks into disposable Harbor tasks without becoming a
second benchmark authority.

The initial matrix compares the same model across OpenCode, Codex, and Claude
Code with two arms:

- `none`: native harness tools only;
- `hashmarks`: the identical task image plus one trial-scoped Hashmarks stdio
  MCP exposure.

Hashmarks is installed into **both** images. Only MCP exposure varies, avoiding a
package/image confound. No user/global MCP registration is benchmark authority.

## Run

Set the existing Hashmarks source authority and the one model to compare in
`.env`:

```dotenv
HASHMARKS_BENCH_SOURCE=/absolute/path/to/Hashmarks
BENCHMARK_HARBOR_MODEL=<provider/model>
BENCHMARK_HARBOR_EXECUTABLE=harbor
BENCHMARK_PASSTHROUGH_ENV_KEYS=OPENAI_API_KEY,ANTHROPIC_API_KEY
```

Only list credential variable **names** in the file. Their values must already
exist in the host environment. The bridge writes them to a run-local mode-0600
Harbor env file and never includes values in agentsCookbook receipts.

Model-free readiness for the full matrix:

```sh
make benchmark-check MATRIX=harbor-full
```

Fast one-task matrix:

```sh
make benchmark-new MATRIX=harbor-smoke
```

Full three-task / three-attempt matrix:

```sh
make benchmark-new MATRIX=harbor-full
```

List runs, resume an interrupted run, and report without invoking a model:

```sh
make benchmark-runs MATRIX=harbor-full
make benchmark-resume MATRIX=harbor-full RUN_ID=000001
make benchmark-status MATRIX=harbor-full RUN_ID=000001
make benchmark-report MATRIX=harbor-full RUN_ID=000001
```

### Read-only workspace integrity

The repository-location verifier uses one bounded native Git porcelain
observation to qualify the workspace, including staged/unstaged tracked edits,
new untracked files, and ignored files. The sole exception is the required
`.agentscookbook-answer.json` transport file, which must be an ordinary file
of at most 64 KiB. A symlink answer, extra generated file, failed Git status,
or unbounded status output denies the read-only reward even when the reported
owner/path is correct. The verifier keeps `tracked_clean` for compatible
answer-evidence readers and now exposes `workspace_status_error`,
`unexpected_change_count`, and bounded `unexpected_change_paths`.

This check detects current worktree changes; it is **not** proof that the agent
never modified and restored a file or changed Git metadata. The source
checkout and experiment task authorities are still independently frozen
before execution.

The report publishes per-harness bare/Hashmarks success rates,
`hashmarks_uplift`, and the bare-vs-Hashmarks `harness_spread`. A positive
spread reduction is evidence that the portable repository-intelligence layer
reduced harness sensitivity.

### Explain the mechanism, not only the score

New Harbor runs also freeze two bounded artifacts into each immutable
agentsCookbook result bundle when Harbor provides them:

- the root ATIF `trajectory.json`;
- `answer.json` from the verifier, containing only the observed
  `path`/`symbol` answer, expected answer, match result, and tracked-tree
  cleanliness.

The analyzer intentionally ignores ATIF `reasoning_content` and conversational
message text. It consumes only structured tool calls, linked observations, and
token metrics, then maps host-specific tools through agentsCookbook's existing
tool-routing vocabulary.

A captured ATIF trajectory is not automatically complete tool-order evidence.
Malformed steps, non-list `tool_calls`, malformed call records, missing function
names, and empty trajectories retain explicit `tool_order_issue_codes` and
`tool_order_issue_count`. Valid observed calls remain visible, but a partial
trajectory has `tool_order_complete=false`, unknown routing and treatment,
and cannot prove `NEVER_INVOKED`, fewer tool calls, native discovery displacement,
or a positive paired mechanism attribution. The component ablation analyzer
likewise excludes those quartets from qualified aggregate denominators.
ATIF steps with no `tool_calls` field are valid: the field is optional.

This is *parser completeness* for the captured trace, not cryptographic
attestation that a host emitted every call. Host exposure and delivery
authenticity must still be established separately.

For a completed bare/Hashmarks pair with the same campaign, task, harness,
model, and replicate, the mechanism report records independent dimensions such
as:

- `FAIL_TO_PASS`, `PASS_TO_PASS`, `PASS_TO_FAIL`, or `FAIL_TO_FAIL`;
- `FIRST_CHOICE`, `LATE_RESCUE`, or `NEVER_INVOKED`;
- observed successful treatment, no usable result, never invoked, or unknown;
- native discovery/search/read displacement;
- tool-call and token deltas;
- wrong-to-correct versus same-answer transitions;
- whether a repository path returned by Hashmarks was later used by a native
  read.

Inspect the latest full Harbor run with:

```sh
make benchmark-harness-explain
```

or a specific run:

```sh
make benchmark-harness-explain RUN_ID=000001
```

The default for this convenience target is `HARBOR_MATRIX=harbor-full`; override
it explicitly when needed.

Positive mechanism labels are **supported associations**, not causal proof.
`NEVER_INVOKED` is stronger in the opposite direction: agentsCookbook records
the pair as `NOT_ATTRIBUTABLE` and refuses to credit Hashmarks for that outcome
delta. Partial campaigns may be inspected with `./benchmark explain
--allow-incomplete`, but their mechanism evidence is marked
`INSPECTION_ONLY` and is not persisted as a qualified mechanism report.

### Controlled component ablations

A Harbor ablation matrix declares one Hashmarks MCP `component` and four
explicit arm roles:

- `bare`: native harness tools only;
- `full`: the complete canonical Hashmarks MCP contract;
- `remove`: the complete contract with exactly that component withheld;
- `only`: only that component advertised.

The matrix freezes the role-to-subject mapping and requires the remove/only
tool projections to match the declared component exactly. Hashmarks owns the
generic server-side projection mechanism; agentsCookbook owns which projection
constitutes an experimental arm.

Model-free preflight calls Hashmarks readiness for every restricted catalog and
freezes the canonical source-contract identity, exact projected tools,
independently observed catalog, projection identity, and the ablation contract
before model work. That same ablation contract is transported into every trial
receipt. Generated Harbor MCP config bytes are checksum-bound into campaign
authority, so same-path replacement or projection drift fails resume before
another model trial.

For every completed matched quartet, the report checks observed Hashmarks
invocations from the ATIF trace against the frozen tools in each arm. A bare arm
calling Hashmarks, a removal arm invoking the withheld component, or an only
arm invoking a different Hashmarks operation invalidates treatment
qualification. Unknown tool spellings or incomplete tool-order evidence remain
explicitly unqualified.

These are negative checks on observable calls, not proof of which MCP tools the
host advertised. The report therefore keeps
`observed_catalog_advertisement_proven=false`. Positive necessity/sufficiency
classification additionally requires observable invocation of the declared
component in the relevant full or only arm.

The report uses one generic schema for every component:

- **necessity-style:** full Hashmarks versus full Hashmarks minus the component;
- **sufficiency-style:** bare versus the component as the only Hashmarks tool.

Possible classifications include
`NECESSARY_AND_SUFFICIENT_CONTRAST`, `NECESSITY_SIGNAL`,
`SUFFICIENCY_SIGNAL`, `REDUNDANT_OR_OTHER_HASHMARKS_PATH`, and
`NO_ISOLATED_COMPONENT_SIGNAL`. The report never upgrades these replicate-level
contrasts into universal causal proof and always keeps
`positive_causal_proof_claimed=false`.

Qualified component campaigns persist `reports/ablation.json`.

**Aggregate component effects use a stricter denominator than campaign
completion.** Per-harness success rates and component contrasts are computed
only from fully matched quartets where all four outcomes are PASS/FAIL and the
frozen treatment passes ATIF call-projection qualification. A reward-only,
partial-trajectory, treatment-unqualified, or incomplete quartet remains
inspectable but cannot contribute to apparent component uplift.

The report explicitly counts `matched_quartets`,
`qualified_complete_quartets`, `treatment_unqualified_quartets`,
`incomplete_outcome_quartets`, and `excluded_matched_quartets`; each
`by_harness` entry exposes its own matched/qualified denominator. When no
qualified quartet exists, aggregate success rates and contrasts remain `null`
rather than treating missing evidence as failure.

#### Semantic localization: `task_evidence`

The existing `harbor-ablation-*` matrices use prompts where the implementation
owner is not already known. This matches the Hashmarks MCP contract: semantic
localization should route to `task_evidence` before exploratory native search.

Run smoke then full:

```sh
make benchmark-check MATRIX=harbor-ablation-smoke
make benchmark-new MATRIX=harbor-ablation-smoke

make benchmark-check MATRIX=harbor-ablation-full
make benchmark-new MATRIX=harbor-ablation-full
```

Inspect without another model invocation:

```sh
make benchmark-harness-ablation
make benchmark-harness-ablation RUN_ID=000001
```

#### Known exact symbol: `find`

The `harbor-find-ablation-*` matrices use a distinct task population where the
exact symbol name is explicitly supplied and only its path is unknown. This
matches the Hashmarks MCP contract's routing rule for `find`; reusing the
semantic-localization prompts would confound the component test with the wrong
routing intent.

Three exact-symbol task definitions live beside the held-out suite for Harbor
projection only:

- `lookup-known-symbol-paths-under`;
- `lookup-known-symbol-sync-remove-stale-paths`;
- `lookup-known-symbol-run-poll-delay`.

They are intentionally **not** listed in the canonical held-out
`experiment.json`, so adding the `find` experiment does not expand or mutate
the native 12-task benchmark population.

Run smoke then full:

```sh
make benchmark-check MATRIX=harbor-find-ablation-smoke
make benchmark-new MATRIX=harbor-find-ablation-smoke

make benchmark-check MATRIX=harbor-find-ablation-full
make benchmark-new MATRIX=harbor-find-ablation-full
```

Inspect the latest qualified `find` run:

```sh
make benchmark-harness-find-ablation
make benchmark-harness-find-ablation RUN_ID=000001
```

The generic command remains available for future components:

```sh
make benchmark-harness-ablation \
  HARBOR_ABLATION_MATRIX=harbor-find-ablation-full
```

#### Known edit, downstream consequences: `change_impact`

The `harbor-change-impact-ablation-*` matrices reuse the frozen
`behavioral-v4` mutation corpus. Each task starts from a checksum-bound
post-mutation repository baseline, asks the agent to make one narrowly allowed
edit, and grades both the edited bytes and the downstream implementation /
verification evidence with the suite's existing independent command oracle.

This is intentionally different from semantic localization: the changed owner
is already known, and the question is what else the change affects.

```sh
make benchmark-check MATRIX=harbor-change-impact-ablation-smoke
make benchmark-new MATRIX=harbor-change-impact-ablation-smoke

make benchmark-check MATRIX=harbor-change-impact-ablation-full
make benchmark-new MATRIX=harbor-change-impact-ablation-full

make benchmark-harness-change-impact-ablation
```

The full campaign is 4 tasks × 3 harnesses × 4 arms × 3 replicates = 144 trials.

#### Existing change, evidence revalidation: `post_change`

The `harbor-post-change-ablation-*` matrices reuse the four
`behavioral-v4/post_change` cases. These cover both edit and read-only
freshness/reuse decisions after a changed path already exists. This isolates
whether `post_change` contributes beyond the rest of Hashmarks when the agent
must decide what evidence is stale, reusable, or newly relevant.

```sh
make benchmark-check MATRIX=harbor-post-change-ablation-smoke
make benchmark-new MATRIX=harbor-post-change-ablation-smoke

make benchmark-check MATRIX=harbor-post-change-ablation-full
make benchmark-new MATRIX=harbor-post-change-ablation-full

make benchmark-harness-post-change-ablation
```

The full campaign is also 144 trials.

#### External/derived observations: `correlate_evidence`

The `harbor-correlate-evidence-ablation-*` matrices reuse the four
`behavioral-v4/correlation` cases. Their prompts are deliberately not owner
localization or changed-path questions. They provide bounded external or
derived observations and ask the agent to preserve evidence semantics:

- runtime-path to repository-source mapping without inventing causation;
- conflicting line/symbol claims without silently selecting an owner;
- ambiguous symbol evidence and a known-missing repository member as separate
  states;
- independent revision comparison while retaining runtime provenance.

That matches Hashmarks's `correlate_evidence` contract: correlate bounded
observations while preserving ambiguity, provenance, completeness, and source
equivalence.

```sh
make benchmark-check MATRIX=harbor-correlate-evidence-ablation-smoke
make benchmark-new MATRIX=harbor-correlate-evidence-ablation-smoke

make benchmark-check MATRIX=harbor-correlate-evidence-ablation-full
make benchmark-new MATRIX=harbor-correlate-evidence-ablation-full

make benchmark-harness-correlate-evidence-ablation
```

The full campaign is 4 tasks × 3 harnesses × 4 arms × 3 replicates = 144 trials.
As with the other component experiments, positive attribution requires an
observable `correlate_evidence` invocation in the relevant full/only arm and
never becomes a universal causal claim.

#### Correlated provider declarations: `repository_declarations`

The `harbor-repository-declarations-ablation-*` matrices reuse the four
`behavioral-v4/declarations` cases. They test whether the agent preserves
declaration authority rather than collapsing independently sourced provider
claims into one synthetic truth:

- equivalent declarations retain both provider identities rather than picking
  a winner;
- differing declarations remain explicitly differing without selecting an
  authoritative provider;
- declared A↔B and B↔C relationships do not silently prove A↔C or merge
  provider namespaces;
- incomplete provider coverage does not become proof of absence or
  equivalence.

That matches Hashmarks's `repository_declarations` contract: project
correlated repository declarations while preserving provenance, ambiguity,
coverage, and freshness.

```sh
make benchmark-check MATRIX=harbor-repository-declarations-ablation-smoke
make benchmark-new MATRIX=harbor-repository-declarations-ablation-smoke

make benchmark-check MATRIX=harbor-repository-declarations-ablation-full
make benchmark-new MATRIX=harbor-repository-declarations-ablation-full

make benchmark-harness-repository-declarations-ablation
```

The full campaign is again 144 trials. Positive attribution requires an
observable `repository_declarations` invocation in the relevant full/only
arm; incomplete or treatment-unqualified quartets remain outside aggregate
component-effect denominators.

#### Frozen dependency evidence: `dependency_codemap`

The `harbor-dependency-codemap-ablation-*` matrices reuse the four
`behavioral-v4/dependency_delta` cases. These deliberately present already
materialized dependency evidence; the agent is not asked to execute uv, Maven,
or another package manager. The cases test whether dependency semantics are
projected correctly rather than reconstructed from tool execution:

- uv component selection moving from one version to another without inferring
  why it changed;
- Maven relationship/scope changes that leave component selection unchanged;
- same-version uv source selection separated from marker-only relationship
  change;
- Maven classifier selection distinguished from effective-scope change.

That matches Hashmarks's `dependency_codemap` contract: project dependency
evidence as observation, explanation, or endpoint comparison without executing
a package manager.

```sh
make benchmark-check MATRIX=harbor-dependency-codemap-ablation-smoke
make benchmark-new MATRIX=harbor-dependency-codemap-ablation-smoke

make benchmark-check MATRIX=harbor-dependency-codemap-ablation-full
make benchmark-new MATRIX=harbor-dependency-codemap-ablation-full

make benchmark-harness-dependency-codemap-ablation
```

The full campaign is 4 tasks × 3 harnesses × 4 arms × 3 replicates = 144
trials. Positive attribution requires an observable `dependency_codemap`
invocation in the relevant full/only arm; missing tool-order evidence or
treatment drift leaves the quartet outside qualified component aggregates.

#### Query-facet ablation: `verification-explanation`

`repository_intelligence_query` is a multi-facet facade, so agentsCookbook
does **not** treat the whole tool as one mechanism. A selector-aware ablation
can bind one structured call argument to one product-owned facet. The first
such matrix uses:

```text
component: repository_intelligence_query
selector:  surface_name = verification-explanation
```

and the four `behavioral-v4/verification` cases. Their oracle asks for a
focused repository-native verifier, runner, argv/scope, or closely related
verification evidence.

The treatment arms are:

- `none`: no Hashmarks MCP;
- `hashmarks`: full Hashmarks tools and all canonical query surfaces;
- `hashmarks-no-verification-explanation`: full tool catalog, but exactly
  that query facet withheld;
- `hashmarks-verification-explanation-only`: only
  `repository_intelligence_query`, restricted to exactly that facet.

The facet catalog is not duplicated in agentsCookbook. Model-free preflight
reads the canonical surface list from Hashmarks readiness, derives the two
subsets, asks Hashmarks to qualify each projected server, and freezes selected
plus independently observed surfaces into treatment authority. Generated MCP
config then carries exact repeated `--query-surface` arguments.

ATIF attribution is selector-aware. A call to
`repository_intelligence_query(surface_name="freshness")` does not count as
invoking `verification-explanation`; a call to a facet withheld by the frozen
treatment disqualifies that quartet. Only bounded structured
`tool + surface_name` evidence is retained for this gate—model reasoning and
unrelated tool arguments are not consumed.

```sh
make benchmark-check MATRIX=harbor-verification-explanation-ablation-smoke
make benchmark-new MATRIX=harbor-verification-explanation-ablation-smoke

make benchmark-check MATRIX=harbor-verification-explanation-ablation-full
make benchmark-new MATRIX=harbor-verification-explanation-ablation-full

make benchmark-harness-verification-explanation-ablation
```

The full campaign is again 144 trials. The same generic ablation report remains
the authority; it records both `component` and `selector` and still keeps
`positive_causal_proof_claimed=false`.

### Behavioral Harbor projection authority

Behavioral command-oracle tasks do not treat the mutation fixture as agent
work. agentsCookbook applies the existing suite mutation through the canonical
mutation helper, verifies its SHA-256 and exact changed-path set, and then
freezes a post-mutation workspace manifest before Harbor launches a model.

The Harbor verifier compares the final workspace against that frozen manifest.
Only task-declared `allowed_change_globs` and
`allowed_generated_globs` may differ. It then feeds the agent's bounded JSON
answer to the existing suite `oracle.py` / `cases.json` command oracle and
publishes reward only when both contamination and oracle checks pass.

The projected task bundle therefore binds:

- the mutated repository bytes;
- the mutation identity and changed paths;
- the post-mutation baseline manifest;
- the suite command oracle and cases;
- allowed edit/generated globs;
- the Hashmarks source and projected MCP catalog.

No second behavioral oracle is introduced by Harbor.

### Command-oracle lifecycle qualification

Before applying the frozen mutation or publishing the projected task, the
bridge invokes the suite-owned `oracle.py health <task-id>` using its current
Python interpreter. The bounded 10-second health check must exit zero and
leave workspace bytes unchanged. Failure, timeout, missing executable or
unexpected workspace mutation blocks fixture preparation before model work.
The frozen behavioral projection records `oracle_health` with the successful
operation and time limit; health is not itself a correctness score.

During Harbor verification, the existing suite-owned `oracle.py grade`
receives a distinct 40-second command timeout inside Harbor's 60-second
verifier budget. Missing oracle executables, timeouts, malformed responses,
or stdout/stderr above 64 KiB fail reward closed and leave explicit verifier
evidence. The `oracle.json` diagnostic retains bounded 8 KiB previews,
truncation flags and timeout status. A hung grader can no longer consume the
entire verifier budget without a diagnostic reward. This checks execution
liveness and response integrity; it does not replace the existing lexigram
oracle or prove that the external model saw a specific MCP catalog.

## Boundary

Harbor uses the same numbered run store, durable launch claims, checksum-bound
receipts, and interruption recovery as native benchmarks. Its trial executor
and reward report are backend-specific. A Harbor reward does not certify
Hashmarks subject-tool invocation. Read-only localization keeps the frozen
repository-location verifier; behavioral tasks reuse the suite's frozen
command oracle and mutation authority. Completed `INCOMPLETE` receipts are immutable; resume only executes
pending trials and launches interrupted before receipt publication. Start a
new run after repairing an operational failure.

`harbor-smoke` and `harbor-full` have separate run roots under
`.benchmark-runs/harbor-harness-v1/`. The selected matrix, trial population,
model, Harbor/Docker versions, projected task bytes, and Hashmarks source
identity are frozen before model work. A changed authority requires a new run.

The preflight fails before model work unless the Hashmarks checkout is clean, its
`doctor --mcp` diagnostic reports the current canonical MCP contract, Harbor is
available, Docker is available, all selected tasks satisfy the projection
contract, and explicitly selected credential variables exist.


### Information timing and oracle-aligned evidence

The Harbor mechanism report now exposes a second, **non-causal information
timeline** for completed bare/Hashmarks pairs. It is a richer explanatory
projection than a headline pass rate or a raw tool-call count; it does not
replace the frozen suite oracle or the generic component-ablation evaluator.

Inspect with the existing model-free entrypoint:

```sh
make benchmark-harness-explain RUN_ID=000001
```

Each pair has `information_evidence` with:

- `qualified` and `reason`: explicit observability admission/exclusion;
- `target_alignment`: `ORACLE_TARGET_ONLY`, `ALTERNATE_TARGETS_ONLY`,
  `MIXED_TARGETS`, `NO_STRUCTURED_PATH_TARGETS`, or `UNKNOWN`;
- `arrival_timing`: `BEFORE_NATIVE_DISCOVERY`, `AFTER_NATIVE_DISCOVERY`,
  `NO_NATIVE_DISCOVERY`, `NO_SUBJECT_RESULT`, or `UNKNOWN`;
- `native_read_followthrough`: whether a later *observed native read* named
  the oracle path, another returned path, both, or neither;
- tool-call ordinals, plus the linked ATIF observation step for information
  arrival (which can be later than the tool invocation); native discovery and
  subsequent path-aligned reads are kept separate.

The report summary groups **only qualified pairs** by outcome transition,
arrival timing, target alignment, and follow-through under
`information_outcome_cross_tab`. It separately counts
`information_qualified_pairs` and `information_exclusion_reasons`. Thus
`FAIL_TO_PASS | BEFORE_NATIVE_DISCOVERY | ORACLE_TARGET_ONLY |
ORACLE_PATH_READ` is directly inspectable, while `PASS_TO_FAIL` with an
alternate target is a signal to investigate, **not** proof the target harmed
the agent. Also inspect `FAIL_TO_FAIL` with a correct target: the information
may have been returned too late, left unused, or been insufficient.

The expected path comes only from the frozen verifier's answer evidence,
never from the model's answer or its reasoning. The observation projection
parses bounded structured tool results and tool-call arguments, including JSON
inside MCP text blocks. It compares complete repository-relative paths, never
fuzzy substrings, and never persists raw tool results or agent messages in
this derived report. Duplicate call/observation IDs, missing linked results,
unparseable subject results or MCP text blocks, malformed tool order,
ambiguous same-step result/call ordering, and missing path oracles fail closed to an explicit unqualified/unknown state.

This experiment does **not** measure when the agent mentally adopted a
belief or whether the tool output was attended to. A later native read is
observable follow-through only. Opaque native read arguments are explicitly
unknown rather than evidence that follow-through never occurred. Agents can use information without a native
read, and a native read does not establish causation. For behavioral command
oracles without a path oracle, information alignment remains unqualified
rather than inventing a path-correctness grade. Use the existing
`full/remove/only/bare` component ablations for stronger controlled contrasts.


### Semantic evidence: what information arrived, not just which file

The post-run Harbor mechanism report now adds `semantic_information_evidence`
for the frozen behavioral-v4 **command oracle** tasks (dependency transitions,
change impact, declarations, correlation, freshness, negative evidence, and
verification). This complements the path-specific `information_evidence`
added in PR #211. It does not change the canonical task prompts, experiment
arms, oracle correctness, execution, reward, or component ablation.

After the existing behavioral oracle runs, its verifier writes the **same**
canonical `cases.json` expected atoms into its verifier-only `answer.json`
artifact. Those atoms are never placed in the agent workspace or supplied
to the agent during execution. The mechanism evaluator reads this frozen
bundle and the existing oracle's field-level rubric; it **does not** call
an oracle or derive a second answer key from agent output.

For each treated pair, it records:
- `claim_alignment`: `ALIGNED_ONLY`, `DIVERGENT_ONLY`,
  `MIXED_OR_CONFLICTING`, `NO_COMPARABLE_CLAIMS`, or `UNKNOWN`;
- exact expected-field **names** (not values) found in structured
  Hashmarks responses, separated into aligned, divergent, and conflicted;
- `first_subject_observation_step`, `first_aligned_observation_step`,
  `first_divergent_observation_step`, and `first_native_discovery_step`;
- arrival `BEFORE_NATIVE_DISCOVERY`, `AFTER_NATIVE_DISCOVERY`,
  `NO_NATIVE_DISCOVERY`, or `UNKNOWN_SAME_STEP`;
- `final_answer_overlap`: whether correct or divergent returned claim
  values also appeared in the verifier-observed final answer;
- qualification/exclusion codes and the explicit
  `agent_attention_proven=false` and `causal_influence_claimed=false`.

The existing `make benchmark-harness-explain` target exposes
`summary.semantic_outcome_cross_tab` keyed by paired outcome transition,
arrival timing, alignment, and final-answer overlap. Only fully completed
PASS/FAIL pairs with qualified structured evidence contribute. The
`semantic_exclusion_reasons` denominator separately counts legacy bundles
without frozen semantic expected atoms, incomplete traces, unlinked/ambiguous
observations, invalid rubrics, and incomplete outcomes. The output contains
no expected or observed atom **values** and no model reasoning/messages.

An example pattern worth investigating is `FAIL_TO_FAIL` with an
early, oracle-aligned claim that the final answer did not repeat. Another is
`PASS_TO_FAIL` with a divergent claim repeated in the final answer.
Neither is proof the model read or adopted the evidence; tool output
availability and answer co-occurrence are not agent cognition.
`ALIGNED_ONLY` also does not imply the entire tool response is accurate:
only fields named by the frozen task oracle can be compared. Opaque
narrative output, mixed values for the same field, and uncertain call/result
ordering do not silently turn into an absence or a positive attribution.

Use the existing bare/full/remove/only ablations for stronger component
contrasts. These new post-run projections explain the **mechanism to inspect**,
not universal causal effectiveness. Historical Harbor bundles without the
new expected-atom artifact remain inspectable but do not retroactively
acquire semantic qualification.


### Component-isolated semantic evidence for controlled ablations

The `ablation` report now carries a **separate diagnostic denominator** for
oracle-aligned semantic evidence in the four-arm `bare/full/remove/only`
experiments. This builds on the post-grade semantic evidence projection rather
than introducing a second oracle or a competing ablation scorer.

For each matched quartet, `semantic_component_evidence.full` and
`semantic_component_evidence.only` examine **only returned observations from
the exact frozen component**, including the exact `surface_name` for
selector-based experiments. Evidence from `find`, `task_evidence`, or another
Hashmarks tool cannot be credited to `repository_declarations` merely because
it was in the same full-arm trajectory. A result containing the expected
semantic atom is available evidence; a repeated value in the final answer is
co-occurrence, **not proof of the agent attending to or adopting it**.

The existing command:

```sh
make benchmark-harness-ablation RUN_ID=000001
```

now exposes:

- Per-quartet `semantic_component_evidence` with full/only claim alignment,
  arrival relative to native discovery, final-answer overlap, and a qualification
  reason. Only expected **field names** appear; values and agent messages are not
  reproduced in the report.
- `summary.semantic_qualified_quartets` and
  `summary.semantic_exclusion_reasons`.
- `summary.semantic_outcome_cross_tab`, grouping qualified contrasts by
  existing classification, full/only outcomes, alignment, arrival, and repeated
  claims. This helps distinguish *correct information exposed before discovery
  and associated with a successful only-arm outcome* from *late, conflicting,
  or unused information associated with a failure*.
- Per-harness `semantic_qualified_quartets` alongside the **unchanged**
  `qualified_complete_quartets` and success-rate contrasts.

This diagnostic denominator is deliberately stricter: a quartet must already
be treatment-qualified and have four complete PASS/FAIL outcomes, both
`full` and `only` arms must have invoked the declared component/selector,
and both component-filtered semantic ATIF projections must be qualified.
Missing post-grade oracle atoms, partial ATIF, unlinked observations, opaque
results, non-invocation, and treatment violations remain **excluded**, not
converted to failed/negative information exposure. Historical bundles without
semantic post-grade receipts stay inspectable but do not qualify retroactively.

A component may still help through non-atom mechanisms (e.g., better discovery
or smaller search space); `NO_COMPARABLE_CLAIMS` is not an ineffectiveness
verdict. The control experiment's existing necessity/sufficiency-style
contrasts remain descriptive replicate-level evidence, never universal
causal proof. No models are invoked by this report.

### Scoped SCIP/LSP relationship evidence timing

After Hashmarks PRs #409–#413, the same immutable ATIF tool results can
contain qualified `task_evidence.semantic_relationships` records. The Harbor
mechanism evaluator now adds `relationship_scope_evidence` to each treated
bare/Hashmarks pair without changing reward, oracle, task, prompts, or execution.

The projection requires a linked structured `task_evidence` tool result with
a resolved owner and self-consistent count scopes. It preserves the difference
between the direct SCIP **outgoing definition count** and the wider
**associated direct producer-claim count**, which may include incoming SCIP or
request-local LSP observations. A zero outgoing count is not evidence of
absent incoming relationships. No additional Hashmarks requests are made.

The returned report describes:
- `SCOPED_SEMANTIC_RETURN`, `NO_SCOPE_RECORD`, `NEVER_INVOKED`, or
  unqualified/unknown evidence with explicit exclusion reasons;
- `BEFORE_NATIVE_DISCOVERY`, `AFTER_NATIVE_DISCOVERY`,
  `NO_NATIVE_DISCOVERY`, or `SAME_STEP_UNORDERED` based on the *linked
  result step*, not the earlier invocation step;
- an **exact** subsequent `structural_locality` request for the same
  `path::qualname` with `result_mode="relationships"`, separate from model
  attention or actual evidence use;
- native search calls observed before and after the semantic return.

The summary includes `relationship_scope_outcome_cross_tab` combining the
qualified return timing, explicit detail-request state, semantic count scope,
paired outcome, and existing paired `native_search_delta`. Incomplete
outcomes, missing/duplicated ATIF links, malformed producer claims, and opaque
results are excluded rather than treated as evidence absence. The paired bare
arm remains the same harness/model/task/replicate. This is **descriptive
correlation**, not a claim that Hashmarks reduced exploration or caused a pass.

Inspect with `make benchmark-harness-explain RUN_ID=000001`. A real A/B
measurement still needs paired runs against explicitly selected Hashmarks
source commits, with identical task/agent/model conditions and successful
campaign admission. These post-run projections run model-free against the
frozen bundles; historical bundles without the new fields are not silently
upgraded. `observed_use_proven`, `agent_attention_proven` and
`causal_influence_claimed` remain false.

## Integrated evidence/evaluation assurance (PR #217)

The model-free Harbor mechanism report now includes
`summary.evaluation_assurance`. It is derived from the same verified
immutable receipts, not a second scorer, second oracle, or another campaign
authority.

- **E217 / E222**: `delivery_evidence` binds each subject invocation to its
  ATIF source-call-linked packet digest, return step, bounded byte count, and
  structural/text presentation parity. `RETURNED` means tool result observed;
  `delivery_state=UNKNOWN` and `application_state=UNKNOWN` remain honest:
  ATIF does **not** independently attest which bytes entered the model input
  context. Tool follow-up is observable behavior, not proof of model cognition.
- **E218**: model-free adversarial tests reject orphan/duplicate/early results,
  forged semantic claims, malformed calls, tool-error envelopes, contradictory
  JSON views, incomplete observations, and unsupported causal upgrades.
- **E219**: headroom-v2 keeps semantic grading separate from output format.
  An isolated bare-agent failure remains `observed` headroom but is no longer
  mislabeled *reproducible*: `reproducibility_state` requires at least two
  semantic failures among three or more gradeable replicates for the same
  task/agent condition. No historical v2 oracle or receipt is regraded.
- **E221**: exact within-harness paired outcome transitions receive a
  deterministic task/harness/model-cluster bootstrap interval only when at
  least eight independent task clusters are observed. Fewer groups show
  `INSUFFICIENT_EVIDENCE` and a null interval; this is **not** a p-value,
  posterior probability, or claim of statistical significance.
- **E223 / E224**: JSON structured-vs-text parity is checked when both
  presentations exist. A matching dual presentation is not a controlled
  presentation experiment; frozen model-backed native/compact/text/structured
  contrasts require a separate admitted intervention campaign.
- **E227 / E228**: the single JSON report provides exact denominators,
  exclusions, headroom, per-harness effects, observed packet states, and paired
  native-search/token deltas. Missing monetary/provider/catalog accounting
  remains unavailable instead of becoming zero.

### E225: two-component tool-catalog factorial

The frozen matrix isolates the interaction of Hashmarks `task_evidence` and
`find` while holding the rest of the catalog unchanged. It has four
factorial tool configurations plus the ordinary bare arm:

| Factorial role | `task_evidence` | `find` |
| --- | --- | --- |
| neither | excluded | excluded |
| a_only | present | excluded |
| b_only | excluded | present |
| both | present | present |

It reuses Harbor's model execution, immutable bundles, treatment identities,
independent answer grading, and ATIF call projection. The new report checks
the exact per-arm tool catalog, source-contract identity, observed forbidden
calls, complete four-way outcomes, and matched task/harness/model/replicate
before emitting the descriptive interaction
`both - a_only - b_only + neither`. Incomplete or contaminated groups are
excluded. Catalog exposure is not inferred from absence of calls. Factorial
records never enter the legacy single-component ablation fallback.

Model-free admission and an explicitly funded run:

```sh
make benchmark-check MATRIX=harbor-factorial-smoke
make benchmark-new MATRIX=harbor-factorial-smoke
make benchmark-check MATRIX=harbor-factorial-full
make benchmark-new MATRIX=harbor-factorial-full
make benchmark-report MATRIX=harbor-factorial-full
```

A qualified full run persists `reports/factorial.json` and the corresponding
`tool_factorial` section in `reports/report.json`. An unqualified run
cannot publish a positive interaction claim. These commands involve model
calls after the model-free checks; CI does not execute them.

### E226 and outstanding empirical boundaries

The existing `context-invariance-v1` suite already runs neutral/placebo/
unsupported-authority/misleading-hint contrasts. Harbor's generic pair report
does not silently call this a bound freshness intervention. A new frozen,
independently reviewed stale/current/replaced-evidence task population is
needed before context/freshness effect claims.

`multidomain-v2` also has 60 pending independent reviews. This PR does not
self-approve them. Presentation interventions need source/runtime support for
changing only the selected result representation; host-level model-input
delivery proofs need a host-owned capture boundary. Until those authorities
exist, the report explicitly records `NOT_ASSESSED`, `NOT_IDENTIFIABLE`,
or `UNKNOWN`, not spurious success.
