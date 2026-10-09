# Harbor cross-harness repository-intelligence matrix

This directory is an **execution projection**, not a second benchmark authority.

The canonical repository task, pinned repository commit/tree, prompt, and oracle
remain owned by the referenced agentsCookbook suite. The bridge admits only
read-only, unmutated `repository-location-json` tasks and projects those facts
into disposable Harbor tasks.

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

## Boundary

Harbor uses the same numbered run store, durable launch claims, checksum-bound
receipts, and interruption recovery as native benchmarks. Its trial executor
and reward report are backend-specific. A Harbor reward does not certify
Hashmarks subject-tool invocation or replace the native repository-location
oracle. Completed `INCOMPLETE` receipts are immutable; resume only executes
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
