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
BENCHMARK_HARBOR_ROOT=.benchmark-runs/harbor-harness-v1
BENCHMARK_HARBOR_PASSTHROUGH_ENV_KEYS=OPENAI_API_KEY,ANTHROPIC_API_KEY
```

Only list credential variable **names** in the file. Their values must already
exist in the host environment. The bridge writes them to a run-local mode-0600
Harbor env file and never includes values in agentsCookbook receipts.

Model-free admission:

```sh
make benchmark-harness-check
```

Fast one-task matrix:

```sh
make benchmark-harness
```

Full three-task / three-attempt matrix:

```sh
make benchmark-harness HARBOR_MODE=matrix
```

Report the latest run without invoking a model:

```sh
make benchmark-harness-report
```

The report publishes per-harness bare/Hashmarks success rates,
`hashmarks_uplift`, and the bare-vs-Hashmarks `harness_spread`. A positive
spread reduction is evidence that the portable repository-intelligence layer
reduced harness sensitivity.

## Boundary

The Harbor bridge is deliberately narrower than the canonical agentsCookbook
campaign runner. It does not mint canonical campaign receipts, replace oracle
review/admission, or claim that a Harbor reward certifies Hashmarks. It exists to
make the Model × Harness × Repository-Intelligence experiment cheap to execute.

The preflight fails before model work unless the Hashmarks checkout is clean, its
`doctor --mcp` diagnostic reports the current canonical MCP contract, Harbor is
available, Docker is available, all selected tasks satisfy the projection
contract, and explicitly selected credential variables exist.
