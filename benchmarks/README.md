# Empirical benchmark framework

This directory owns reusable, product-neutral experiments for agents, tools, evidence systems, and software-engineering outcomes.

## Authority boundary

The harness is the experiment authority. A product under test never grades itself.

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

`run --new` freezes the selected population and immediately executes the full campaign. `run --resume` requires the same frozen selection and authority. `prepare --new` remains an advanced model-free preparation primitive, not the normal `make benchmark-new` workflow. Every later trial compares observed authority and exact task inputs against the campaign receipt before invoking the model. A durable launch claim makes interrupted trials visible. If a process dies before publishing a complete receipt, the next invocation retires that active claim into immutable numbered interruption evidence and starts a new explicit attempt; already completed receipts are reused and never retried. Changed runtime, model, configuration, subject source, workspace input, or selection requires a new saved run.

Native tool discovery and benchmark-subject selection are separate authorities.

Codex, OpenCode, and Enola are normal host-installed tools. The benchmark does not duplicate their standard Linux installation paths or config roots in `.env`. It resolves their executables from the native `PATH`, derives Codex/OpenCode config roots from the host's normal `HOME`, `XDG_CONFIG_HOME`, and `CODEX_HOME` conventions, then records the resolved executable hash, version, native config identity, and effective subject exposure. Native defaults are therefore **observed authority**, not hidden benchmark configuration.

Hashmarks is intentionally different: it is the locally developed product under test, so `HASHMARKS_BENCH_SOURCE` explicitly selects the clean committed checkout and its exact `.venv/bin/hashmarks`. This prevents an unrelated installed Hashmarks from silently replacing the candidate under test.

For native OpenCode and Codex trials, ambient/global MCP registrations are disabled as subject authority. The selected Hashmarks or Enola subject is injected ephemerally from the adapter-owned exact executable/cwd/args. A global MCP registration can therefore exist for normal development without choosing what the benchmark executes.

Participant processes do not inherit arbitrary host environment variables. The harness carries one fixed process-substrate allowlist—`PATH`, locale variables, terminal identity, and equivalent Windows launch variables—so native tools can start. Provider variables must be named explicitly through `BENCHMARK_PASSTHROUGH_ENV_KEYS`. The resulting observed environment is bound into execution identity.

Benchmark settings are parsed once per command by `benchmarks/config.py`. There is no automatic `.env` discovery: readiness, preflight, execution, and native evidence require `--env-file`. Required entries must be present and nonempty in that file even when a CLI flag supplies an override. An exported shell value cannot fill a missing entry. Explicit CLI flags override declared file values for one-off selections; file values override shell values for benchmark authority. Native host discovery and explicitly admitted provider secrets still use the host environment.

Agent Economics remains a benchmark consumer/suite; shared process semantics remain single-owned until that module is promoted to a more generic repository location.

## Python runtime authority

AgentsCookbook's benchmark and qualification Python is stdlib-only. The repository pins Python 3.11 in `.python-version` and executes it through uv. Do not call `python` or `python3` directly from repository-owned entrypoints, CI, or benchmark documentation.

There is intentionally no synthetic Python package/dependency layer just to launch these modules: `uv run --no-project` provides the repository-owned interpreter without inventing package ownership.

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
| `BENCHMARK_SCORE_OUTPUT_PATH` | Score filename inside each saved run | Derived report |

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

`benchmark-new` also executes immediately; it does not stop after preparation. `benchmark-resume` requires the current `BENCHMARK_AGENT` population and selected definitions to match the run's frozen campaign before expensive admission or any model work. Scoring enforces the same frozen agent set.

The remaining targets are optional diagnostics or advanced controls:

```sh
make benchmark-check       # fast runtime readiness
make benchmark-oracle-review-check # oracle qualification check
make benchmark-check-all   # exhaustive model-free preflight
make benchmark-runs        # list saved run IDs
make benchmark-report      # generic framework report
make benchmark-score       # suite-specific scorer
```

The Makefile passes only `.env` and fixed smoke task selectors to the CLI. The configuration loader owns benchmark choices and validates them before runtime work. Codex, OpenCode, and Enola use their installed host conventions; the benchmark observes what resolves. Missing selected-agent choices fail before preflight, execution, reporting, or scoring.

`benchmark-check` answers only **“can each suite agent/subject combination be wired on this machine right now?”** For held-out v1 it checks Codex and OpenCode with bare tools, Hashmarks, and Enola: six pair outcomes, independent of `BENCHMARK_AGENT`. OpenCode's assisted probes supply a live stdio connection check. Only when that connection fails does readiness launch the selected MCP executable and args in the selected cwd and environment with stdin closed and a five-second bound, solely to capture a direct startup failure. A clean exit after stdin closes is inconclusive and adds no diagnostic. Codex readiness proves its native config plus the exact ephemeral subject exposure without invoking a model; it is reported as ready rather than falsely labelled connected. No readiness command retries automatically.

`benchmark-check-all` is an optional intentionally expensive diagnostic: it preflights every frozen definition for the explicitly selected agents. It is not a prerequisite for `make benchmark`, `make benchmark-new`, or `make benchmark-resume`. Held-out v1 has 108 definitions for one agent or 216 when both are listed.

### Advanced direct CLI

The benchmark CLI remains available for automation and explicit one-off selections. Repository Python is owned by uv: invoke it as `uv run --no-project python -m benchmarks ...`. The CLI does not discover `.env`; it resolves declared suite, campaign, agent, and harness settings from the selected file when flags are omitted. The snippets below show optional CLI overrides. Direct `--agent` accepts repeated values or a comma-separated list.

```bash
suite=benchmarks/suites/repository-intelligence/heldout-v1
root=.benchmark-runs/heldout-v1
agents=opencode-native  # or codex-native,opencode-native
```

Fast runtime readiness:

```bash
uv run --no-project python -m benchmarks check \
  --env-file .env \
  --suite "$suite"
```

This command uses no campaign root, harness root, or agent selection and creates no benchmark trial. Add `--agent "$agents"` to diagnose only the selected agents.

For advanced workflows that deliberately separate preparation from execution, create a saved run explicitly before preflight:

```bash
uv run --no-project python -m benchmarks prepare --new --env-file .env
```

```bash
uv run --no-project python -m benchmarks preflight \
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
uv run --no-project python -m benchmarks run \
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
uv run --no-project python -m benchmarks status \
  --suite "$suite" \
  --root "$root" \
  --agent "$agents" \
  --subject hashmarks \
  --subject none

uv run --no-project python -m benchmarks report \
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
uv run --no-project python -m benchmarks run \
  --resume \
  --suite "$suite" \
  --root "$root" \
  --agent "$agents" \
  --subject hashmarks \
  --subject enola
```

The runner reuses valid existing receipts. If the process died during one definition, its prior launch and available event bytes are preserved as numbered `INTERRUPTED` evidence; only that unfinished definition starts a new attempt. Run `benchmarks runs` to list saved IDs and pass `--run-id` to inspect or resume an older one. Status exposes separate integrity, completeness, and qualification checks. Live stderr shows processed definitions separately from verified receipts.

Inspect resumability without invoking any agent:

```bash
uv run --no-project python -m benchmarks status \
  --suite "$suite" \
  --root "$root" \
  --agent "$agents" \
  --subject hashmarks \
  --subject enola
```

`status.complete` means every selected definition has a verified immutable receipt. `status.qualified` additionally requires every receipt to be a valid experimental outcome (`PASS`, `FAIL`, or `NO_QUALIFYING_DEFECT`). A campaign can therefore be structurally complete but not qualified.

Each complete status row includes the receipt's diagnostic stage and reason code when available. Report diagnostics include the same fields and mark older receipts without them as `legacy-inferred`. The detailed diagnostic remains in `result.json`; compact status and report output do not copy tracebacks. A final run summary on stderr reports verified receipts, outcome counts, and qualification. The run exits nonzero when the final selected campaign is not qualified.

Finally:

```bash
uv run --no-project python -m benchmarks report \
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
