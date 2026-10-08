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
