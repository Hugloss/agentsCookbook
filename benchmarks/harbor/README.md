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


## E229–E232: factorial campaign completeness and independent-review handoff

The E217–E228 factorial matrix is **a defined experiment, not a measured
effect**. E229–E232 add two read-only qualification surfaces without creating
a new benchmark runner, another oracle, or a Hashmarks implementation.

### E229–E230: exact campaign grid, verified bundles, and arm consistency

Run the existing model-backed campaign explicitly (this requires configured
Harbor, model credentials, runtime dependencies, and a pinned Hashmarks build):

```sh
make benchmark-check MATRIX=harbor-factorial-smoke
make benchmark-new MATRIX=harbor-factorial-smoke
make benchmark-check MATRIX=harbor-factorial-full
make benchmark-new MATRIX=harbor-factorial-full
```

Then audit **one actual saved campaign** (do not use the sample paths as claims
of a completed run):

```sh
make benchmark-factorial-campaign-audit \
  RESULTS_ROOT=.benchmark-runs/harbor-harness-v1/factorial-full \
  CAMPAIGN_ID=<actual-execution-campaign-id> MODE=matrix
```

For smoke use `MODE=smoke` and the smoke run root. The audit walks immediate
bundle directories and invokes the repository's existing immutable Harbor
bundle verifier; unreadable or corrupt bundles are counted as blockers.
It insists on every `harness × task × replicate × subject` cell: **15 smoke
cells/3 quartets**, **135 full cells/27 quartets**, including the bare control
for each matched quartet. No duplicate, missing, foreign-campaign, out-of-grid,
ungradeable, tool-order-incomplete, source-contract-drift, mixed-model, or
contaminated-bare cell is silently removed from the denominator. Each four-arm
factorial must pass the existing exact tool-catalog/trace treatment audit.

`coverage_state=COMPLETE` is limited to exact, internally consistent run
coverage. It does **not** authorize `empirical_effect_qualified`,
`model_input_delivery_attested` or
`independent_oracle_review_attested`; all remain false without distinct
external authority. A failed `--require-complete` exits nonzero. The audit
does not alter existing scoring or rerun a model.

### E231–E232: independently reviewable case work, not synthetic approval

```sh
make benchmark-eval-readiness
make benchmark-eval-review-queue > /tmp/agentscookbook-independent-review-queue.json
```

The queue enumerates each multidomain case still requiring a review, with a
SHA-256 of the frozen case excluding its mutable review field, plus every
skill without a distinct confusion case. Every queue entry is explicitly
non-approved. For multidomain tasks an independent reviewer must inspect the
pinned repository, fixture digest, source ownership, counterexample and oracle
expectation; for confusion cases, create and independently validate genuine
repository fixtures and a negative oracle, not just an ungrounded scenario.
Reviewer-generated evidence must be checked against the frozen identity in a
separate approval workflow. This PR does not self-approve 60 multidomain cases
or fabricate 54 confusion cases.

### Boundary

Hashmarks owns repository evidence; agentsCookbook owns descriptive
measurement and intervention qualification. ATIF-linked returns are not proof
of visibility or cognition. Presentation parity is not a randomized
representation experiment. The optional campaign audit never runs in CI
against synthetic results to assert actual uplift; tests exercise only
model-free adversarial qualification rules. Independent review and
model-backed intervention campaigns remain explicit follow-on actions.


## E233–E236: externally attested model-input boundary and intervention audit

These read-only qualification tools do **not** turn Harbor's ATIF trace into a
model-input log or add a model-input interception hook to Codex, OpenCode, or
Claude Code. Today the standard Harbor backend **does not** generate the
external signed receipts specified below. They can only be produced by a
separately trusted, instrumented model-invoking host. Until such a host is
integrated, delivery and intervention results remain **UNKNOWN / unrun**.

### E233: independently keyed host input receipt

A Hashmarks tool return is `RETURNED`, not `DELIVERED`. To attest the latter,
a model-invoking **host** must inspect the actual outgoing model request
*after* any result transformation and emit a receipt through a channel
unavailable to the agent and MCP server. It must sign the binding to the
tool packet only when that packet actually appears in the request input.

The receipt schema is
`agentscookbook.host-model-input-attestation.v1`:

- Envelope: `schema`, `campaign_id`, `trial_id`,
  `trajectory_sha256` (SHA-256 of exact ATIF bytes), `deliveries`.
- Every delivery: `host_identity`, `host_build_sha256`,
  `model_request_sha256`, `model_input_sha256`,
  `model_message_sha256`, `packet_sha256`, `call_id_sha256`,
  `model_request_sequence`, `boundary="host-model-request-input"`, and
  `mac_sha256`. All `*_sha256` values are lowercase 64-digit hex.
  `packet_sha256` and `call_id_sha256` must match a **qualified ATIF
  Hashmarks result** rather than a free-text claim.
- MAC: `HMAC-SHA256(key, b"agentscookbook:host-model-input-attestation:v1\\x00"
  + canonical_json({"context": envelope_without_deliveries,
  "delivery": delivery_without_mac}))`. Canonical JSON uses sorted keys,
  compact separators, UTF-8, and rejects nonfinite numbers. Optional
  `intervention` metadata is part of the MAC, never an unsigned annotation.

The trust key **must** be independently generated and inaccessible to trial
workspaces, agent tools, and Hashmarks. The verifier rejects symlinked keys
and group/world-readable key files. Do not put keys, raw prompts, credentials,
or raw model messages into the repository, benchmark outputs, or PRs.

```sh
make benchmark-host-delivery-audit \
  TRAJECTORY=/immutable/run/trial/trajectory.json \
  HOST_ATTESTATION=/external-host/receipts/trial.json \
  HOST_KEY_FILE=/trusted-host-only/host-hmac.key \
  CAMPAIGN_ID=real-campaign-id TRIAL_ID=real-trial-id
```

Invalid/stale/foreign/duplicated/orphaned or unauthenticated receipts never
become delivery proof. Complete coverage yields `delivery_state=PROVEN`
**only in the limited sense of a keyed host assertion about model-request
input**: it does not prove the provider processed the request, the model
noticed the information, or the information influenced an answer. Partial
packet coverage stays `PARTIAL`; no key or receipt leaves it `UNKNOWN`.
The ordinary mechanism and assurance reports intentionally retain their
existing `UNKNOWN` delivery state unless an independent verification
integration supplies qualified proof.

### E234–E235: paired presentation and freshness protocols

`benchmark-intervention-audit` consumes **verified Harbor result bundles**
plus independently signed receipts for those exact trials; it does not create
experimental subjects or synthesize agent traces. A design JSON has precisely:

```json
{
  "schema": "agentscookbook.host-attested-intervention-design.v1",
  "study": "presentation",
  "campaign_id": "replace-with-actual-campaign-id",
  "model": "replace-with-exact-provider-model",
  "harnesses": ["codex"],
  "tasks": ["locate-prefix-path-enumerator"],
  "replicates": 3,
  "arms": {"control": "structured", "variant": "text"}
}
```

For `study="freshness"`, the exact arms are `control="current-generation"`
and `variant="replaced-generation"`. Both require two model-backed,
matched, graded, full-contract `hashmarks` trials per
harness × task × replicate. The externally signed host receipt adds
`intervention` with exactly:

`study`, `arm`, `design_sha256`, `presentation`,
`generation_sha256`, `current_generation_sha256`,
`semantic_sha256`, `catalog_sha256`, `prompt_sha256`,
`oracle_sha256`, `workspace_sha256`, `surface_sha256`.

The design digest uses the canonical JSON above. Every signed packet
in a trial must report the **same** treatment. Presentation comparisons
require identical semantic/generation/catalog/prompt/oracle/workspace
identities, with structured vs text as the only modeled difference and
different surface digests. Freshness comparisons keep the presentation and
current-target generation fixed but deliberately differ in exposed
generation and semantic response identity. The trial source contract
identity must also be unchanged. These are host-attested invariants, not
independently reproduced source-byte proofs.

```sh
make benchmark-intervention-audit \
  DESIGN=/trusted-evaluator/design.json \
  RESULTS_ROOT=/immutable/harbor/run/bundles \
  ATTESTATIONS_ROOT=/external-host/receipts \
  HOST_KEY_FILE=/trusted-host-only/host-hmac.key
```

The receipt for each bundle directory `trial-name` lives at
`ATTESTATIONS_ROOT/trial-name.json`. Its signed `trial_id` must equal
that directory name; its signed campaign must match the frozen design.
Missing/duplicate/foreign/ungradeable trials and uncontrolled changes
block coverage, not merely disappear from denominators. This is **not a
working treatment injector**: implementing verified transformations at each
harness's host boundary remains external work.

### E236: conclusions and safety of interpretation

Only matched `PASS/FAIL` outcomes admitted through the exact host-input
boundary enter the per-harness descriptive contrast (variant minus control).
Task/harness/model-cluster bootstrap intervals are suppressed below eight
independent task clusters, and harnesses are never pooled. Even a complete,
host-attested grid is **not** evidence of true randomization, pre-registered
timestamp authority, independent oracle review, provider consumption,
model attention, or causal product uplift. Those require separately
qualified evidence.

Model-free QA (no model, key, external host or trial needed):

```sh
uv run --no-project python -m unittest benchmarks.tests.test_host_attested_interventions -v
uv run --no-project python -m unittest discover -s benchmarks/tests
make benchmark-eval-readiness
```

**Open external dependencies:** actual host-side model-request instrumentation,
key custody and external durable signatures; real matched interventions and
frozen randomized assignments; independent review of oracle cases. Never
upgrade these to complete merely because the code and tests pass.


## E237–E240: frozen host execution and independent campaign qualification

This is the follow-on to E233–E236. The shipped Python adapter can be
integrated into a **privileged provider-invoking host** using the exact
request bytes and the original Hashmarks return. It is *not* installed into
the current third-party Codex/OpenCode/Claude Code hosts or silently injected
by Harbor. Until a genuine host invokes it on its actual outbound request,
there is **no real host-delivery observation** and no qualifying campaign.

### E237: provider host adapter — actual request, exact message, no forge CLI

`benchmarks/harness/trusted_host_capture.py` exposes
`TrustedModelRequestCapture`. A privileged host must initialize it
**outside the evaluated workspace**, with the frozen manifest, an
owner-only external key, and the exact planned trial. The host then calls
`observe_outbound_request(...)` on the *serialized provider request*
at its outbound request boundary, supplying the corresponding original
Hashmarks return, selected treatment input, and host-observed
catalog/prompt/oracle/workspace identities.

Only the explicit JSON provider envelope with `model` and
`messages=[{"role":"tool","tool_call_id":...,"content":...}]` is
supported. Unknown provider formats reject instead of guessing.
The adapter checks the exact designated tool-call message content,
provider model, returned-packet/source consistency, immutable
manifest assignment, and hashes the actual request bytes.
`prompt_sha256` must match the observed request's non-tool messages
and request settings. The selection must already be reflected in the
request; simply requesting a treatment does not mark it delivered.

After final ATIF capture, the trusted host invokes `finalize()`.
This requires complete immutable ATIF call/result bindings, then
creates an external HMAC receipt without overwriting existing files.
There is **no executable for signing agent-provided data**. The adapter
cannot independently prove that an arbitrary caller is a real
provider host, that provider dispatch succeeded, or that the model
attended to or used the information. Those facts remain separate.

### E238: plan all controlled treatments before work

`benchmarks/harness/trusted_treatments.py` deterministically fixes the
entire `harness × task × replicate × arm` assignment grid under the
original intervention design, one declared seed digest, frozen host
build digest, and source-contract identity. The manifest includes an
identity for each planned trial, paired experiment identity, and explicit
within-pair execution ordinal. It is create-only, and changed arm
assignments, source, design, or missing cells reject on admission.

```sh
make benchmark-treatment-freeze \
  DESIGN=/external/design.json \
  MANIFEST_OUTPUT=/external/pre-work/frozen-manifest.json \
  SOURCE_CONTRACT_ID=sha256:pinned-hashmarks-source \
  HOST_BUILD_SHA256=<64-hex-host-build-digest> \
  ASSIGNMENT_SEED_SHA256=<64-hex-declared-seed-digest>
```

Selection is pure and fail-before-work. Presentation uses **one**
pinned semantic/generation source, returning the same JSON facts
structured or as canonical JSON text. Freshness requires explicit
current and replaced source identities with unequal generations and
semantic digests. Every host must actually install the selected
message into the provider request. The deterministic seed **does
not prove randomized assignment** or externally timestamped preregistration.

### E239: tie Harbor execution back to the frozen assignments

`validate_trial_alignment` enumerates each planned trial and rejects
absent, foreign, duplicate, symlink, mismatched model/harness/task/replicate,
missing full Hashmarks contract, changed contract identity, substituted
host build, wrong arm, or unbound host receipt. The existing intervention
audit additionally verifies external host MACs and exact input facets.
A complete generic Harbor pair report cannot replace these checks.
Identity is resolved once, transported once, executed once, reported once.

### E240: separate custodial seal and conservative decision

`benchmarks/harness/independent_campaign_qualification.py` accepts a
separately signed `agentscookbook.independent-campaign-seal.v1` JSON,
bound to the frozen campaign, manifest digest, design digest, external
anchor digest, review-corpus digest, custodian ID, and boolean assertions
`pre_work_frozen` and `independent_oracle_review_completed`.
Its `mac_sha256` is
`HMAC-SHA256(independent_key, b"agentscookbook:independent-campaign-seal:v1\\x00"
+ canonical_json(seal_without_mac))`.

The review/anchor authority must generate and custody its seal and
secret independently of the host, agent, and Hashmarks. No self-approval
signing command is provided. The qualifier rejects an unverified,
stale, absent or host-key-reused seal, incomplete ATIF delivery,
missing pairs, corrupt/unmatched immutable bundles, and missing
review assertions. Real reviewer labor and externally established
pre-work chronology **must still be independently checked**: a
custodian's signed assertion alone is not a timestamp, proof of
independence, a randomization certificate, or causal evidence.

```sh
make benchmark-independent-campaign-qualify \
  MANIFEST=/external/pre-work/frozen-manifest.json \
  RESULTS_ROOT=/immutable/run/bundles \
  ATTESTATIONS_ROOT=/external-host/receipts \
  HOST_KEY_FILE=/trusted-host/host.key \
  SEAL=/external-reviewer/seal.json \
  INDEPENDENT_KEY_FILE=/external-reviewer/review.key
```

`descriptive_campaign_admitted=true` means that the immutable grid,
host-input boundary receipts, source identities, and externally
key-authenticated custodian claims are consistent. It is not a
causal-impact qualification. Reports always reserve
`causal_effect_proven=false`, `model_attention_proven=false`,
`real_randomization_proven=false`, and
`trusted_pre_work_timestamp_proven=false`.

Regression and model-free evidence:

```sh
uv run --no-project python -m unittest benchmarks.tests.test_trusted_host_campaign -v
uv run --no-project python -m unittest discover -s benchmarks/tests
make benchmark-eval-readiness
```

**Remaining operational work**: add a native provider-host SDK integration
which invokes the boundary adapter on real outgoing requests, independently
custody and anchor the pre-work manifest, verify source and oracle reviews
through actual people, and run the controlled model trials. CI passing
does not close those dependencies.


## E241–E244: controlled HTTPS provider dispatch and strict submission assurance

The E237–E240 host adapter checked a declared outbound request but did not
own the transport. E241 introduces a **runnable** HTTPS transport with a
narrow protocol and explicit host custody, rather than pretending Harbor
can intercept requests made inside native third-party agent harnesses.

### E241: actual outbound body, one attempt, no redirect

A privileged host imports
`benchmarks.harness.trusted_http_provider.dispatch_verified_chat_request`
and passes an E237 `TrustedModelRequestCapture` plus the **actual serialized**
OpenAI-compatible Chat Completions JSON body. The host still owns:
the frozen manifest, model credentials, full original tool response, its
real task/prompt/oracle/workspace identities, and external evidence storage.

For this limited adapter the HTTP endpoint must be pinned to the host-owned
`approved_origin`, use TLS, have exactly the path
`/v1/chat/completions`, and have no embedded URL credentials/query/fragment.
The transport suppresses environment-provided proxy routes, disables
redirect following, sends **one** JSON POST with its original request bytes,
and accepts only a bounded 2xx JSON object containing a nonempty
`choices` array. The host must supply a syntactically correct provider
conversation; this function does not construct agent reasoning, generate a
prior tool call, implement all provider message shapes, or retry on error.
An invalid envelope/unsupported provider remains inadmissible.

The receipt is emitted only when `TrustedModelRequestCapture.finalize()`
matches every source call and packet to the immutable completed ATIF.
The transport must have observed a successful provider HTTP response before
`finalize()` can publish an attestation. Failed/ambiguous requests cannot
retry within the same capture and cannot produce a successful
transport-submission receipt. Raw request and response bodies are not
persisted by this transport.

### E242: verify the selected treatment actually reached the transport

Before HTTP work the host checks the frozen trial identity, single selected
Hashmarks packet, pinned semantic/generation source, specific model and tool
call, one and only one tool-message slot, and a prompt digest derived from
the actual request settings and non-tool messages. These are observable
body-level invariants, not inferred from returned tool packets.

Every successful host-submission record includes a MAC-protected
`transport` object:

```json
{
  "boundary": "https-response",
  "endpoint_sha256": "<64-hex>",
  "http_status": 200,
  "response_sha256": "<64-hex>",
  "response_bytes": 1024
}
```

The verifier distinguishes `delivery_state=PROVEN` (key-holder asserts
tool-message inclusion) from `provider_submission_state=SUBMITTED`
(key-holder asserts one successful HTTPS response from its pinned
transport). Both remain host assertions: neither is proof of model
attention, provider inference, or a causal outcome. A receipt without
the signed transport object keeps submission `UNKNOWN`. Partial coverage
does not become complete.

### E243–E244: audit every arm under one external authority

A stricter qualification entrypoint re-checks every planned trial's
immutable ATIF and independent host HMAC, requires `SUBMITTED` for
*all* planned cells, verifies the existing frozen source/assignment and
paired intervention constraints, and separately validates the review
custodian's signed seal. No completed cell is inferred from a missing
bundle, no replayed request is a new observation, and one valid arm is
not sufficient for a paired claim.

```sh
make benchmark-provider-campaign-qualify \
  MANIFEST=/external/pre-work/frozen-manifest.json \
  RESULTS_ROOT=/immutable/run/bundles \
  ATTESTATIONS_ROOT=/external-host/receipts \
  HOST_KEY_FILE=/trusted-host/host.key \
  SEAL=/external-reviewer/seal.json \
  INDEPENDENT_KEY_FILE=/external-reviewer/review.key
```

Descriptive campaign admission requires every independent check to pass.
The report explicitly withholds provider-processing proof, real randomization,
trusted pre-work chronology, model attention, and causal attribution.
An externally signed pre-work or human-review *assertion* must still be
supported by independent operational evidence.

Model-free attack regressions (faked HTTPS responses, **no network traffic**):

```sh
uv run --no-project python -m unittest benchmarks.tests.test_trusted_http_provider -v
uv run --no-project python -m unittest discover -s benchmarks/tests
```

**Not shipped:** native OpenCode/Codex/Claude Code transport interception,
real verified provider trials, independently timestamped preregistration,
or completed independent oracle review. No experimental result is inferred
from mocks or a successful CI run.


## E245–E248: native-host feasibility and independently verified campaign provenance

These checkpoints deliberately distinguish a **working first-party HTTPS
provider transport** from the opaque model-request boundaries of native
Codex, OpenCode, and Claude Code. They do not create another coding agent
or transplant Hashmarks search into agentsCookbook.

### E245: explicit native-harness boundary register

`make benchmark-native-host-readiness DESIGN=/external/design.json`
inspects the frozen design without contacting a model. The shipped
integration status is:

| Harness | What can be observed | Native model-input capture qualified? |
|---|---|---|
| Codex / codex-native | Agent trace and tool results | **No** |
| OpenCode / opencode-native | Agent trace and tool results | **No** |
| Claude Code | Harbor trace and tool results | **No** |
| OpenAI Responses routing probe | Provider-managed MCP outputs and direct API response | **No** |
| trusted-http-chat | First-party controlled HTTPS body and submission receipt | **Not a native agent harness** |

The existing OpenAI Responses probe may truthfully claim routed
`mcp_call` evidence, but provider-managed MCP output is not proof of
exact model-input packet inclusion. Independent host HMAC keys and a
synthetic provider response likewise do not magically identify a
native third-party provider boundary.

No `native-host-supported=true` user-supplied field can override this.
Adding a genuine native integration requires a separately reviewed
version-bound adapter and observed provider-request tests before changing
the register.

### E246–E247: cross-trial transport provenance

`make benchmark-host-transport-provenance` re-verifies the signed host
input AND successful HTTPS response binding for **every planned arm**,
against exact frozen trial IDs and expected host identity, host build,
`model_request_sequence=1`, selected arm and design, and the exact
approved SHA-256 endpoint identity. Within each pair the host build,
host identity, endpoint, catalog, prompt, oracle and workspace hashes
must all be stable. One missing, foreign, tampered, re-signed-but-drifted
or symlinked trial fails the population. This is read-only and cannot
produce its own receipts.

```sh
make benchmark-host-transport-provenance \
  MANIFEST=/external/pre-work/frozen-manifest.json \
  RESULTS_ROOT=/immutable/run/bundles \
  ATTESTATIONS_ROOT=/external-host/receipts \
  HOST_KEY_FILE=/trusted-host/host.key \
  APPROVED_ENDPOINT_SHA256=<sha256-of-approved-full-provider-url> \
  EXPECTED_HOST_IDENTITY=<independent-registered-host-name>
```

These identities are host assertions verified with an independently
custodied key, not remote provider-signed statements. A TLS 2xx response
is evidence of bounded host submission, not reasoning or attention.

### E248: descriptive empirical decision gate

`make benchmark-empirical-campaign-decision` jointly requires
authenticated provider submission, the independently sealed campaign,
exact immutable Harbor bundles, complete intervention pair coverage,
and cross-trial stable transport provenance. It also requires observed
control failures (task headroom), and at least **eight distinct task
clusters within each harness** before a descriptive interval population
is admitted. Missing or unknown grades never enter an effect estimate.
Each harness is assessed separately; heterogeneous model/harness
populations are never pooled into a product-winner claim.

```sh
make benchmark-empirical-campaign-decision \
  MANIFEST=/external/pre-work/frozen-manifest.json \
  RESULTS_ROOT=/immutable/run/bundles \
  ATTESTATIONS_ROOT=/external-host/receipts \
  HOST_KEY_FILE=/trusted-host/host.key \
  SEAL=/external-reviewer/seal.json \
  INDEPENDENT_KEY_FILE=/external-reviewer/review.key \
  APPROVED_ENDPOINT_SHA256=<64-hex> \
  EXPECTED_HOST_IDENTITY=<registered-host>
```

The strongest possible state from these tools is
`submission_bounded_descriptive_population_qualified`. The following
are **always explicitly unproven**: true native-harness capture, actual
independent human case reviews, externally trusted preregistration
chronology, genuine assignment randomness, provider consumption,
model attention, and causal Hashmarks uplift. Those require
**new observed external evidence**, not another reporting boolean.

Run the model-free attack ring:

```sh
uv run --no-project python -m unittest benchmarks.tests.test_native_provenance_and_empirical_decision -v
uv run --no-project python -m unittest discover -s benchmarks/tests
```

The additional tests include valid-but-synthetic HMAC receipts,
substituted endpoint/host-build identities, duplicate trial replay,
missing control, cross-arm prompt drift, modified signed transport,
unreviewed host status and insufficient control headroom.
They are **not** a completed empirical benchmark.

**Pending after this bundle:** wire a genuine instrumented host boundary
for at least one native agent/version, execute controlled matched
provider-backed tasks with independent run custody, and obtain real
independent oracle reviews. Do not describe provider-owned MCP routing
as the missing native transport hook.


## E249–E252: opt-in pinned OpenCode custom-provider gateway

This is the **first executable trial-scoped native OpenCode provider route**
in the evaluator. It does not replace the existing native OpenCode
benchmark adapter and is not enabled implicitly. It is a standalone
one-shot OpenAI-compatible route for controlled evaluation.

Official OpenCode V1 provider documentation describes
`provider.<name>.npm="@ai-sdk/openai-compatible"` with
`options.baseURL` for a custom provider and `enabled_providers` for
provider restriction. See
[OpenCode provider configuration](https://opencode.ai/docs/providers/)
and [OpenCode config](https://opencode.ai/docs/config/).
The opt-in runner freezes those values in a *private, create-only*
`opencode.json` and selects `agentscookbook-captured/<model>`.
It also isolates HOME/XDG config/data/cache and suppresses unrelated
LLM credentials in the launched child environment.

### E249 — exact executable and provider-config admission

A trial needs an already-frozen E238 assignment for
`harness="opencode-native"` (or `"opencode"`), pinned OpenCode
executable SHA-256, exact observed `opencode --version`, a model
ID, and one independently pinned source payload
(`generation_sha256`, `semantic_sha256`, `content`).
The semantic digest MUST match the canonical JSON content.
The executable is checked before and after running, and config
files are create-only under a fresh private run root.

**Do not reuse an existing OpenCode configuration** as gateway authority.
OpenCode can merge managed, global, and project configuration, so the
generated allowlist is an intended constraint—not proof of the
runtime's final effective provider selection. Any foreign/native
requests must still be rejected by the isolated gateway. The native
provider package, its effective settings, other plugin hooks, and
process egress are not yet independently attested.

### E250 — actual loopback request boundary

The runner launches the pinned native OpenCode process directly,
not through a shell, and points its configured OpenAI-compatible
provider to a loopback-only HTTP gateway with a per-trial bearer
token. The token is not proof of OS process identity: an evaluated
child could read its own environment. The upstream API credential
stays with the privileged host and is **not** passed to OpenCode.

A maximum of four pre-tool provider requests can pass through the
host-owned TLS client for native tool selection. These are
**unattested** and never count as Hashmarks delivery. When exactly
one tool-result message appears, the gateway compares it byte-for-byte
by JSON value against the frozen selected Hashmarks result. It then
uses the existing E241 signed transport to validate and dispatch the
actual request exactly once. Its bounded response is returned
unchanged to the native client, without a second provider call.
Wrong model, missing/duplicate tool message, changed selected
content, auth failure, over-budget requests, and retries fail closed.
Only OpenAI Chat Completions JSON with the currently supported
single `role="tool"` message form is supported.

### E251 — fail-before-work qualification and observed execution

Use a **fresh** `RUN_ROOT`, a git-bound disposable `WORKSPACE`,
a frozen original subject `CURRENT_SOURCE` JSON and, for freshness,
the explicit `REPLACED_SOURCE` JSON. Specify the OpenCode binary and
observed SHA/version; every authority is a required argument.

```sh
export BENCHMARK_UPSTREAM_API_KEY=<privileged-host-only-provider-secret>
make benchmark-opencode-native-gateway \
  MANIFEST=/external/prework/frozen-manifest.json \
  TRIAL_ID=<frozen-native-trial-id> \
  OPENCODE_BIN=/trusted/bin/opencode \
  OPENCODE_SHA256=<sha256-executable> \
  OPENCODE_VERSION=<exact-version-output> \
  RUN_ROOT=/private/new-trial-dir \
  WORKSPACE=/disposable/git-workspace \
  PROMPT_FILE=/external/frozen-prompt.txt \
  CURRENT_SOURCE=/external/verified-hashmarks-packet.json \
  HOST_KEY_FILE=/trusted-host/host.key \
  HOST_IDENTITY=<trusted-provider-host-id> \
  UPSTREAM=https://api.openai.com/v1/chat/completions \
  APPROVED_ORIGIN=https://api.openai.com \
  CATALOG_SHA256=<64-hex> ORACLE_SHA256=<64-hex> \
  WORKSPACE_SHA256=<64-hex>
```

The native process must successfully exit AND the gateway must have
relayed exactly one selected tool-result request before
`native_gateway_route_completed` can become true. A normal
`opencode run` exit on its own is not evidence of native model-input
delivery. Invalid or unobserved runs return nonzero status without
upgrading evidence. This launcher does **not** infer a tool result
from agent prose or synthesize a host-signed ATIF.

### E252 — what is and isn't empirically qualified

The gateway can prove to its own key holder which HTTP request body it
received and submitted. **It cannot prove that only the real OpenCode
process could speak on loopback.** OS-bound peer identity/egress
confinement, immutable native OpenCode session export, ATIF binding,
real task oracle review, and externally anchored campaign authority
are required before claiming native execution provenance or a
model-backed Hashmarks effect. The result intentionally reports:

- `host_receipt_finalized=false`
- `native_process_origin_proven=false`
- `native_model_input_delivered_proven=false`
- `causal_improvement_proven=false`

The earlier `TrustedModelRequestCapture.finalize` can only sign when
**real immutable ATIF** is separately available and exactly matches
the observed packet; never create an ATIF from the gateway request
to manufacture delivery proof. The E248 empirical gate remains
conservative, and no campaign has been run here.

Model-free attack regressions cover SHA/version drift, fail-before-work
admission, exact gateway model/packet matching, unknown messages,
pre-evidence budgets, one-shot response relay, no retries, create-only
config, child credential isolation and native-exit-without-evidence:

```sh
uv run --no-project python -m unittest benchmarks.tests.test_opencode_native_gateway -v
uv run --no-project python -m unittest discover -s benchmarks/tests
```
