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

### Controlled `task_evidence` ablation

The separate `harbor-ablation-*` matrices isolate the first Hashmarks component
without changing the model, task image, repository authority, harness, or
replicate. Each matched quartet contains:

- `none`: native harness tools only;
- `hashmarks`: the complete canonical Hashmarks MCP contract;
- `hashmarks-no-task-evidence`: the same canonical contract with only
  `task_evidence` withheld;
- `hashmarks-task-evidence-only`: only `task_evidence` advertised.

Hashmarks owns the generic server-side projection mechanism. agentsCookbook owns
which projection constitutes an experimental arm. Model-free preflight calls
Hashmarks readiness for every restricted catalog and freezes the canonical
source-contract identity, exact projected tools, independently observed catalog,
and projection identity before model work.

The generated Harbor MCP config bytes are also checksum-bound into campaign
authority. A same-path config replacement therefore fails resume before another
model trial instead of being silently regenerated.

Run the one-task smoke first:

```sh
make benchmark-check MATRIX=harbor-ablation-smoke
make benchmark-new MATRIX=harbor-ablation-smoke
```

Then run the full three-task / three-replicate campaign:

```sh
make benchmark-check MATRIX=harbor-ablation-full
make benchmark-new MATRIX=harbor-ablation-full
```

Inspect the qualified component analysis without another model invocation:

```sh
make benchmark-harness-ablation
make benchmark-harness-ablation RUN_ID=000001
```

Qualified ablation campaigns persist `reports/ablation.json`.

The report deliberately separates two contrasts:

- **necessity-style:** full Hashmarks versus full Hashmarks minus
  `task_evidence`;
- **sufficiency-style:** bare versus `task_evidence` only.

A positive contrast is credited to `task_evidence` only when ATIF proves that
the relevant full or only arm actually invoked that operation. For example,
full PASS + removal FAIL is only `SUPPORTED_NECESSITY_CONTRAST` when the full
arm visibly called `task_evidence`; otherwise it is marked unattributable.
Likewise, bare FAIL + task-evidence-only PASS requires an observed
`task_evidence` call before it becomes `SUPPORTED_SUFFICIENCY_CONTRAST`.

These are controlled replicate-level contrasts, not universal causal proof.
The report always keeps `positive_causal_proof_claimed=false`; repeated results
across tasks, replicates, and harnesses are the evidence for deciding whether a
component effect generalizes.

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
