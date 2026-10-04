# Empirical benchmark framework

This directory owns reusable, product-neutral experiments for agents, tools, evidence systems, and software-engineering outcomes.

## Authority boundary

The harness is the experiment authority. A product under test never grades itself.

Repository-location scoring keeps semantic correctness and answer-format compliance separate. One unambiguous JSON object, whether bare, in one JSON fence, or in one JSON fence surrounded by prose, may be semantically gradeable; only the bare exact object is format-compliant. Multiple fences, duplicate keys, malformed JSON, or prose with only inline JSON remain ungradeable. Any change to this interpretation advances the frozen experiment/scoring authority before a new campaign.

A benchmark suite freezes repository commit and tree identity, task, mutation digest, oracle identity, conditions, budgets, and scoring before campaign execution. Observed outcomes are preserved as `PASS`, `FAIL`, `INCOMPLETE`, `INVALID`, `CONTAMINATED`, or `NO_QUALIFYING_DEFECT`; infrastructure failures are never silently converted into product failures.

The optional [multidomain v2 suite](suites/repository-intelligence/multidomain-v2/README.md)
adds frozen external fixtures and a separate model-free evidence diagnostic. It
runs only when explicitly requested. No benchmark target is a dependency of the
Hashmarks release workflow.

The [behavioral v4 suite](suites/repository-intelligence/behavioral-v4/README.md)
adds eight repository-intelligence dimensions and reports ordered lexigram grades for
authority, resolution, evidence preservation, and paired assistance. It is an explicit
research suite and is not a release gate.

## Model

`suite -> experiment -> condition -> trial definition -> observed execution`

Subjects and agents are replaceable participants. Hashmarks, Enola, Codex, local models, test selectors, and future tools are adapters, not schema concepts.

Definition identity binds the frozen experiment, task, condition, trial, and paired replicate ID. Execution identity additionally binds observed subject, agent, oracle, harness, environment, and mutation authority. Re-running the same frozen task against a different product/model version therefore creates a different execution identity instead of overwriting or reusing an older result.

New suites use explicit `replicate_ids` for paired stochastic observations. The legacy `seed` field remains readable for historical receipts; it was never transported as a provider sampling seed. A real `provider_seed`, if supported later, must be independently observed and bound to execution authority. Reports treat disagreement across replicates as evidence, with no scored retries.

Each trial uses isolated HOME, TMP, and XDG roots where the agent contract requires them, bounded process execution, sealed raw event evidence, an independently healthy oracle, and a create-once verified result receipt. A trial is resumably complete only when its result, checksum, completion record, and bound artifacts agree.

## Shared execution and admission authority

Benchmark command execution reuses the repository's existing `scripts.agent_economics.bounded_process` authority instead of maintaining a second weaker process runner.

Trial admission is single-owned by `benchmarks.harness.admission`:

`materialize exact source -> apply frozen mutation -> prepare subject -> prepare agent -> healthcheck oracle -> bind observed authority`

Both `preflight` and `run` use that same path. Preflight is diagnostic and never invokes the coding agent or publishes a trial result.

`campaign-audit` uses the same campaign authority observer as `run` across every selected task/condition. It checks global runtime and subject identity, task-scoped native configuration, and paired input equality without invoking a model or publishing campaign authority. It reports pending oracle reviews separately and exits 2 until they are complete. Run it before an expensive campaign; an audit result is diagnostic and never authorizes inference.

Runtime readiness is deliberately separate from trial admission. `benchmark-check`/the `check` command never selects or materializes a task, applies a mutation, runs an oracle, derives a trial/execution identity, inspects receipts, or invokes a model. It creates one disposable smoke workspace, verifies shared subject prerequisites once, and checks each distinct agent/subject pair, including bare conditions, once. The held-out suite therefore produces six pair outcomes rather than expanding its 216 task/condition/replicate definitions. The disposable workspace is deleted when the command exits; rerunning the check is always an explicit user action.

`run --new` freezes the selected population and immediately executes the full campaign. `run --resume` requires the same frozen selection and authority. `prepare --new` remains an advanced model-free preparation primitive, not the normal `make benchmark-new` workflow. Every later trial compares observed authority and exact task inputs against the campaign receipt before invoking the model. A durable launch claim makes interrupted trials visible. If a process dies before publishing a complete receipt, the next invocation retires that active claim into immutable numbered interruption evidence and starts a new explicit attempt; already completed receipts are reused and never retried. Changed runtime, model, configuration, subject source, workspace input, or selection requires a new saved run. Canonical status/report/score refreshes share the same run-store owner: an inspection performed while execution owns the store stays inspection-only, and canonical derived data is recomputed after acquiring the lock so an older observation cannot overwrite newer run state.

Native tool discovery and benchmark-subject selection are separate authorities.

Codex, OpenCode, and Enola are normal host-installed tools. The benchmark does not duplicate their standard Linux installation paths or config roots in `.env`. It resolves their executables from the native `PATH`, derives Codex/OpenCode config roots from the host's normal `HOME`, `XDG_CONFIG_HOME`, and `CODEX_HOME` conventions, then records the resolved executable hash, version, native config identity, and effective subject exposure. Native defaults are therefore **observed authority**, not hidden benchmark configuration.

Hashmarks is intentionally different: it is the locally developed product under test, so `HASHMARKS_BENCH_SOURCE` explicitly selects the clean committed checkout and its exact `.venv/bin/hashmarks`. This prevents an unrelated installed Hashmarks from silently replacing the candidate under test.

For native OpenCode and Codex trials, ambient/global MCP registrations are not subject authority. The selected Hashmarks or Enola subject is injected ephemerally from the adapter-owned exact executable/cwd/args. For OpenCode, an enabled native registration with the same name as the selected benchmark subject is an admission conflict and fails before model work; the benchmark never silently disables or rewrites the user's native configuration. A disabled registration may remain for normal development because it cannot compete with the injected benchmark runtime. OpenCode native configuration is freshly observed for every admission; task-scoped base-config snapshots are not reused as authority. The selected subject runtime identity binds executable bytes and, for Enola, normalized config semantics. Hashmarks additionally binds its clean committed source checkout because an unchanged launcher can still import changed editable source.

Participant processes do not inherit arbitrary host environment variables. The harness carries one fixed process-substrate allowlist—`PATH`, locale variables, terminal identity, and equivalent Windows launch variables—so native tools can start. Provider variables must be named explicitly through `BENCHMARK_PASSTHROUGH_ENV_KEYS`. The resulting observed environment is bound into execution identity.

Benchmark settings are parsed once per command by `benchmarks/config.py`. There is no automatic `.env` discovery: readiness, preflight, execution, and native evidence require `--env-file`. Required entries must be present and nonempty in that file even when a CLI flag supplies an override. An exported shell value cannot fill a missing entry. Explicit CLI flags override declared file values for one-off selections; file values override shell values for benchmark authority. Native host discovery and explicitly admitted provider secrets still use the host environment.

Agent Economics remains a benchmark consumer/suite; shared process semantics remain single-owned until that module is promoted to a more generic repository location.

## Python runtime authority

AgentsCookbook's benchmark and qualification Python is stdlib-only. The repository pins Python 3.11 in `.python-version` and executes it through uv. Do not call `python` or `python3` directly from repository-owned entrypoints, CI, or benchmark documentation.

There is intentionally no synthetic Python package/dependency layer just to launch these modules. The repository-owned `./benchmark` front door relocates execution to the agentsCookbook root and delegates interpreter ownership to `uv run --no-project`, so callers never select a `.venv/bin/python`, `PYTHONPATH`, or neighboring repository runtime.

## Recommended campaign workflow

### Authority vocabulary

Keep deliberate benchmark choices separate from native host discovery:

| Setting | Meaning | Authority/lifetime |
| --- | --- | --- |
| `HASHMARKS_BENCH_SOURCE` | Clean committed Hashmarks checkout being measured | Explicit product source authority |
| `BENCHMARK_AGENT` | One native agent or a comma-separated list for preflight/run/report/score | Mandatory selected-agent authority; no default |
| `BENCHMARK_OPENCODE_AGENT` | Exact OpenCode agent persona to execute | Explicit benchmark semantic choice |
| `BENCHMARK_PASSTHROUGH_ENV_KEYS` | Comma-separated provider variables explicitly admitted into participant processes | Optional provider environment authority |
| `BENCHMARK_SUITE_PATH` | Committed suite definition inside agentsCookbook | Benchmark source/configuration |
| `BENCHMARK_CAMPAIGN_ROOT` | Ignored store of numbered campaigns under `runs/`; the newest run is selected by default | Generated campaign evidence |
| `BENCHMARK_HARNESS_REPO_ROOT` | agentsCookbook checkout containing the runner | Harness source authority |
| `BENCHMARK_SCORE_SCRIPT_PATH` | Optional suite-specific scorer | Specialized reporting authority |
| `BENCHMARK_SCORE_OUTPUT_PATH` | Score filename inside each saved run's `reports/` directory | Derived report |

Not configured in `.env`:

- `enola`, `codex`, and `opencode` executables are resolved from native `PATH`;
- Codex uses native `CODEX_HOME` when set, otherwise `$HOME/.codex`;
- OpenCode uses native `HOME` and `XDG_CONFIG_HOME` (or `$HOME/.config`);
- all resolved executable/config identities are observed and recorded.

A **suite path is not an output directory**. A **campaign root is not source configuration**. A native agent's config root is not subject executable authority. These distinctions are enforced so one configured authority cannot silently stand in for another.

For local human-driven campaigns:

```sh
cp -n .env.example .env
# edit .env and set the authorities used by the selected suite
```

The example stores every run under ignored `.benchmark-runs/heldout-v1/runs/<run_id>/`. Each completed trial publishes its own receipt immediately; aggregate JSON and scores are derived later. The per-trial receipts are the durability boundary.

Human-facing derived outputs are kept separately from raw evidence:

```text
.benchmark-runs/heldout-v1/runs/<run_id>/
├── results/          # authoritative receipts, events, and agent traces
├── cache/
├── work/
└── reports/          # small shareable output
    ├── status.json
    ├── report.json
    ├── decision-evidence.json
    └── score.json
```

`decision-evidence.json` is a compact derived first-read view over `report.json`: runtime/host instability, semantic misses, strict-format behavior, subject adoption/assistance evidence, and explicit observability gaps. It performs no ranking or recommendation.

`make benchmark-status`, `make benchmark-report`, and `make benchmark-score` refresh their normal outputs; `benchmark-report` also refreshes `decision-evidence.json`. `make benchmark-reports` refreshes the whole shareable set through the single completed-report owner: scoring is staged and must succeed before the canonical first-read artifacts are refreshed. Canonical files under `reports/` always describe the run's exact frozen campaign selection **and the suite authority frozen at admission**. Selector subsets, `report --allow-incomplete`, or inspection under changed suite authority never replace canonical first-read artifacts. Intentional scoring reinterpretation belongs to the explicit `regrade-score` path rather than canonical report refresh. Share or archive only `reports/` for ordinary benchmark review; keep `results/` when raw execution evidence is needed for audit or debugging.

In the selected Hashmarks source checkout, install its locked MCP extra with `uv sync --frozen --extra mcp --group test` before running readiness. A correct `HASHMARKS_BENCH_SOURCE` path alone does not install the MCP server dependency.

Set one or both execution agents explicitly in `.env` before selected-agent work; omission is a hard failure for those targets:

```dotenv
BENCHMARK_AGENT=opencode-native
# Or: BENCHMARK_AGENT=codex-native,opencode-native
```

For normal use, the benchmark is start-and-leave:

```sh
make benchmark
```

If there is no unfinished run with the same frozen selection, this creates a new numbered run and executes the full population selected by `BENCHMARK_AGENT`. If the latest matching run is unfinished, it refuses to guess and tells you to choose explicitly:

```sh
make benchmark-resume  # continue the frozen run
make benchmark-new     # intentionally start a separate fresh run
```

`benchmark-new` also executes immediately; it does not stop after preparation. `benchmark-resume` requires the current `BENCHMARK_AGENT` population and selected definitions to match the run's frozen campaign before expensive admission or any model work. Before preflight, preparation, or execution can begin, the harness also verifies that the selected suite scorer exists, belongs to that suite, accepts the exact frozen-definition interface (`--results`, `--output`, `--agent`, repeated `--definition-id`), and has a canonical score filename suitable for the run's `reports/` directory. Scoring enforces the same frozen agent set.

The remaining targets are optional diagnostics or advanced controls:

```sh
make benchmark-check       # fast runtime readiness
make benchmark-doctor      # same model-free runtime authority diagnostics
make benchmark-oracle-review-check # oracle qualification check
make benchmark-check-all   # exhaustive model-free preflight
make benchmark-runs        # list saved run IDs
make benchmark-report      # print report + save report/decision-evidence
make benchmark-score       # save reports/<score filename>
make benchmark-reports     # refresh the complete shareable reports set
```

The Makefile passes only `.env` and fixed smoke task selectors to the CLI. The configuration loader owns benchmark choices and validates them before runtime work. Codex, OpenCode, and Enola use their installed host conventions; the benchmark observes what resolves. Missing selected-agent choices fail before preflight, execution, reporting, or scoring. Remote repository mirrors are also single-owned per repository identity: clone/fetch/materialization holds one non-blocking cache lock, and a competing command fails before Git work instead of sharing a mutable mirror generation.

OpenCode benchmark trials are deliberately single-turn. The benchmark overlay disables native OpenCode auto-compaction for the trial so OpenCode cannot inject synthetic continuation user turns after the benchmark prompt. Admission verifies that this resolves before execution; model/provider and repository-local native config remain observed and frozen as before. Every model invocation gets a unique operation ID in its session title, and session discovery also rejects sessions older than that operation's start time, so stale sessions cannot be adopted by a newer trial. Native OpenCode config, OpenCode executable bytes, selected-subject runtime identity, and source-backed subject identity are revalidated around execution; a generation change makes the result incomplete instead of publishing it as comparable evidence. After a successful OpenCode process exits, the shared runtime may boundedly reread that same operation-owned session export while its terminal assistant text is still being persisted. This never invokes the model again, never creates another benchmark attempt, and still leaves a genuinely textless session incomplete after the observation bound.

`benchmark-check` answers only **“can each suite agent/subject combination be wired on this machine right now?”** For held-out v1 it checks Codex and OpenCode with bare tools, Hashmarks, and Enola: six pair outcomes, independent of `BENCHMARK_AGENT`. OpenCode's assisted probes supply a live stdio connection check. Only when that connection fails does readiness launch the selected MCP executable and args in the selected cwd and environment with stdin closed and a five-second bound, solely to capture a direct startup failure. A clean exit after stdin closes is inconclusive and adds no diagnostic. Codex readiness proves its native config plus the exact ephemeral subject exposure without invoking a model; it is reported as ready rather than falsely labelled connected. No readiness command retries automatically.

`benchmark-check-all` is an optional intentionally expensive diagnostic: it preflights every frozen definition for the explicitly selected agents. It is not a prerequisite for `make benchmark`, `make benchmark-new`, or `make benchmark-resume`. Held-out v1 has 108 definitions for one agent or 216 when both are listed.

### Host-neutral tool-routing diagnostics

Tool-selection diagnostics score semantic routing rather than host-specific tool names. Trace projection classifies calls as `subject-repository-intelligence`, `native-search`, `native-read`, `shell`, `tool-router`, or `other`. The required subject call must complete before the first native repository-discovery class; wrapper/router calls do not count by themselves.

This lets OpenCode names such as `grep`/`read` and ChatGPT-style names such as `mcp__GitHub__search`/`mcp__GitHub__fetch_file` use the same scoring contract. Subject namespaces are normalized too, so `hashmarks_task_evidence`, `tools.hashmarks.task_evidence`, and `mcp__hashmarks__task_evidence` represent the same operation.

A host catalog is admissible only when both the required subject tool and at least one native discovery class are visible. Missing Hashmarks is `ENVIRONMENT_BLOCKED`, not a routing failure; only a READY catalog can answer whether the host selected Hashmarks before native repository discovery.

A captured host catalog can be checked without invoking a model:

```bash
./benchmark tool-routing-catalog \
  --catalog host-tools.json \
  --subject hashmarks
```

The catalog file may be a JSON list of tool names or an object with a `tools` list containing names or `{"name": "..."}` entries. Exit 0 means `READY`; exit 2 means `ENVIRONMENT_BLOCKED`.

The ordered tool trace is a separate authority. Normalize an external host run into this small capture shape rather than pretending it is an OpenCode campaign:

```json
{
  "schema": "agents-cookbook-tool-routing-trace.v1",
  "host": "chatgpt",
  "catalog_sha256": "sha256:<digest printed by tool-routing-catalog>",
  "calls": [
    {
      "tool": "mcp__hashmarks__task_evidence",
      "status": "completed",
      "result_bytes": 1200
    },
    {
      "tool": "mcp__GitHub__search",
      "status": "completed",
      "input": {"query": "checkout discount owner"}
    }
  ]
}
```

The capture owns only observed tool name/order/status/input/result evidence. It must carry the exact `catalog_sha256` emitted by `tool-routing-catalog`; a catalog/trace generation mismatch is rejected before scoring. It must not supply derived fields such as `tool_class`, `ordinal`, or router observability. A wrapper call may include observable `nested_calls`; without them an orchestration router is treated as opaque and cannot produce a false Hashmarks-first PASS.

Score a READY catalog and its matching trace without executing a model:

```bash
./benchmark tool-routing-trace \
  --catalog host-tools.json \
  --trace host-trace.json \
  --subject hashmarks \
  --output routing-score.json
```

Outcomes are `PASS` when the required subject call completed with an observable nonempty result before native discovery, `FAIL` when observable native discovery won first, `UNKNOWN` when ordering/result evidence is insufficient, and `ENVIRONMENT_BLOCKED` when the host catalog was not admissible. Exit codes are respectively 0, 1, 3, and 2. The score records canonical hashes of both input artifacts and recomputes all semantic classifications itself.

### Advanced direct CLI

The repository-owned `./benchmark` launcher is the canonical CLI for automation and explicit one-off selections. It resolves the harness root before delegating to uv, so invocation is independent of the caller's current Python environment. The CLI does not discover `.env`; it resolves declared suite, campaign, agent, and harness settings from the selected file when flags are omitted. The snippets below show optional CLI overrides. Direct `--agent` accepts repeated values or a comma-separated list.

```bash
suite=benchmarks/suites/repository-intelligence/heldout-v1
root=.benchmark-runs/heldout-v1
agents=opencode-native  # or codex-native,opencode-native
```

Fast runtime readiness:

```bash
./benchmark check \
  --env-file .env \
  --suite "$suite"
```

This command uses no campaign root, harness root, or agent selection and creates no benchmark trial. Add `--agent "$agents"` to diagnose only the selected agents.

For advanced workflows that deliberately separate preparation from execution, create a saved run explicitly before preflight:

```bash
./benchmark prepare --new --env-file .env
```

```bash
./benchmark preflight \
  --env-file .env \
  --suite "$suite" \
  --root "$root" \
  --harness-root . \
  --agent "$agents" \
  --subject hashmarks \
  --subject none
```

Selecting `--subject hashmarks` selects only Hashmarks conditions. If a paired bare control is wanted, request `--subject none` explicitly; the selection layer never adds controls implicitly.

Then run the exact same explicit selection:

```bash
./benchmark run \
  --resume \
  --env-file .env \
  --suite "$suite" \
  --root "$root" \
  --harness-root . \
  --agent "$agents" \
  --subject hashmarks \
  --subject none
```

Status and report do not execute participants, so they need only the suite, campaign results, and the same explicit selection:

```bash
./benchmark status \
  --suite "$suite" \
  --root "$root" \
  --agent "$agents" \
  --subject hashmarks \
  --subject none

./benchmark report \
  --suite "$suite" \
  --root "$root" \
  --agent "$agents" \
  --subject hashmarks \
  --subject none
```

Preflight reports every selected frozen definition as one of:

- `READY` — source, mutation, subject, agent, workspace binding, and oracle admission succeeded;
- `COMPLETE` — the same observed execution identity already has a valid experimental outcome receipt;
- `INCOMPLETE` / `INVALID` / `CONTAMINATED` — the same classifications used by execution admission;
- `RECORDED_INCOMPLETE`, `RECORDED_INVALID`, or `RECORDED_CONTAMINATED` — an immutable non-outcome receipt already exists for that execution identity;
- `INVALID_RESULT` / `ERROR` — corrupt persisted evidence or a preflight infrastructure error.

Existing callers may pass `--cache` and `--work` without `--results` for a diagnostic preflight. In that mode preflight does not inspect existing receipts.

Then run the exact same selection:

```bash
./benchmark run \
  --resume \
  --suite "$suite" \
  --root "$root" \
  --agent "$agents" \
  --subject hashmarks \
  --subject enola
```

The runner reuses valid existing receipts. If the process died during one definition, its prior launch and available event bytes are preserved as numbered `INTERRUPTED` evidence; only that unfinished definition starts a new attempt. Run `./benchmark runs --env-file .env` to list saved IDs and pass `--run-id` to inspect or resume an older one. Status exposes separate integrity, completeness, and qualification checks. Live stderr shows processed definitions separately from verified receipts.

Inspect resumability without invoking any agent:

```bash
./benchmark status \
  --suite "$suite" \
  --root "$root" \
  --agent "$agents" \
  --subject hashmarks \
  --subject enola
```

`status.complete` means every selected definition has a verified immutable receipt. `status.qualified` additionally requires every receipt to be a valid experimental outcome (`PASS`, `FAIL`, or `NO_QUALIFYING_DEFECT`). A campaign can therefore be structurally complete but not qualified.

Each complete status row includes the receipt's diagnostic stage and reason code when available. Report diagnostics include the same fields, plus a bounded human-readable receipt `reason`, and mark older receipts without structured diagnostics as `legacy-inferred`. The detailed diagnostic remains in `result.json`; compact status and report output do not copy tracebacks or diagnostic detail. A final run summary on stderr reports verified receipts, outcome counts, and qualification. A completed run exits successfully after its canonical reports are persisted even when the campaign is not qualified; use `benchmark-status --require-qualified` when qualification itself must gate the shell command.

Finally:

```bash
./benchmark report \
  --suite "$suite" \
  --root "$root" \
  --agent "$agents" \
  --subject hashmarks \
  --subject enola
```

The same selectors should be used across preflight, run, status, and report. Bare controls are included only when explicitly selected or when the full frozen suite is run without subject filters.

### Immutable outcomes and interruption evidence

A published `INCOMPLETE`, `INVALID`, or `CONTAMINATED` receipt is evidence and is never deleted or silently overwritten. A process interruption before any complete receipt exists is different: it is preserved as immutable numbered attempt evidence and the unfinished definition may resume with a new explicit attempt. If the underlying infrastructure problem is corrected but observed execution authority does not change, start a new saved run instead of mutating the old evidence. If observed tool/config authority changes, execution identity changes naturally and the new execution can coexist.

`--root` selects the run store; each numbered run owns its `cache/`, `work/`, and `results/`. A legacy single-directory campaign remains selectable as `--run-id legacy`. Frozen suite definitions and verified per-trial receipts remain authority.

## Method

Native runtime readiness (optional, explicit) -> frozen input -> preflight admission (optional, explicit) -> isolated execution -> observed execution identity -> independent oracle -> sealed events -> immutable verified receipt -> status/resume -> aggregate only valid evidence.

Do not change a frozen task, mutation, oracle, or scoring contract after seeing a result. Create a new suite/experiment version instead.
