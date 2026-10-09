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
