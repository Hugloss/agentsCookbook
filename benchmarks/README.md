# Empirical benchmark framework

This directory owns reusable, product-neutral experiments for agents, tools, evidence systems, and software-engineering outcomes.

## Authority boundary

The harness is the experiment authority. A product under test never grades itself.

A benchmark suite freezes repository commit and tree identity, task, mutation digest, oracle identity, conditions, budgets, and scoring before campaign execution. Observed outcomes are preserved as `PASS`, `FAIL`, `INCOMPLETE`, `INVALID`, `CONTAMINATED`, or `NO_QUALIFYING_DEFECT`; infrastructure failures are never silently converted into product failures.

## Model

`suite -> experiment -> condition -> trial definition -> observed execution`

Subjects and agents are replaceable participants. Hashmarks, Enola, Codex, local models, test selectors, and future tools are adapters, not schema concepts.

Definition identity binds the frozen experiment/task/condition/trial/seed. Execution identity additionally binds observed subject, agent, oracle, harness, environment, and mutation authority. Re-running the same frozen task against a different product/model version therefore creates a different execution identity instead of overwriting or reusing an older result.

Each trial uses isolated HOME, TMP, and XDG roots where the agent contract requires them, bounded process execution, sealed raw event evidence, an independently healthy oracle, and a create-once verified result receipt. A trial is resumably complete only when its result, checksum, completion record, and bound artifacts agree.

## Shared execution and admission authority

Benchmark command execution reuses the repository's existing `scripts.agent_economics.bounded_process` authority instead of maintaining a second weaker process runner.

Trial admission is single-owned by `benchmarks.harness.admission`:

`materialize exact source -> apply frozen mutation -> prepare subject -> prepare agent -> healthcheck oracle -> bind observed authority`

Both `preflight` and `run` use that same path. Preflight is diagnostic and never invokes the coding agent or publishes a trial result.

Native agent configuration and benchmark-subject execution are separate authorities.

For native OpenCode trials, the explicitly configured OpenCode executable, home, config root, and agent persona own the native model/provider/auth/permission configuration. The selected benchmark subject is injected ephemerally from its adapter's exact executable, arguments, cwd, and environment. The harness proves the effective subject executable and workspace binding before agent work and binds that exposure into execution authority. Ambient/global OpenCode MCP registrations may be observed and disabled, but they never choose the Hashmarks or Enola executable under test.

For native Codex trials, the explicitly configured Codex executable and `CODEX_HOME` own the native model/auth configuration. Ambient Codex MCP registrations are disabled for the trial. The selected Hashmarks or Enola subject is injected ephemerally from the same adapter-owned exact exposure used by other agents, so a global Codex MCP registration cannot substitute another product installation.

The benchmark never creates or edits repository-local `opencode.json` to register a subject. Hashmarks is selected only from `HASHMARKS_BENCH_SOURCE/.venv/bin/hashmarks`; Enola is selected only from `ENOLA_BENCH_EXECUTABLE`. Participant processes do not inherit arbitrary host environment variables. Provider variables must be named explicitly through `BENCHMARK_PASSTHROUGH_ENV_KEYS`, and the resulting explicit environment is bound into execution identity.

There is no automatic `.env` discovery in the benchmark CLI and no default harness root. Local Make targets pass `--env-file .env`, `--suite`, `--root`, and `--harness-root` explicitly. Direct CLI callers must provide the same authorities themselves.

Agent Economics remains a benchmark consumer/suite; shared process semantics remain single-owned until that module is promoted to a more generic repository location.

## Recommended campaign workflow

### Authority vocabulary

Keep source, runtime, and output roles separate:

| Setting | Meaning | Authority/lifetime |
| --- | --- | --- |
| `HASHMARKS_BENCH_SOURCE` | Clean committed Hashmarks checkout being measured | Product source authority |
| `ENOLA_BENCH_EXECUTABLE` | Exact Enola executable being measured | Product executable authority |
| `BENCHMARK_CODEX_EXECUTABLE` | Exact Codex executable | Native-agent executable authority |
| `BENCHMARK_CODEX_HOME` | Explicit Codex config/auth root | Native Codex configuration authority |
| `BENCHMARK_OPENCODE_EXECUTABLE` | Exact OpenCode executable | Native-agent executable authority |
| `BENCHMARK_OPENCODE_HOME` | Explicit OpenCode home | Native OpenCode user/config authority |
| `BENCHMARK_OPENCODE_CONFIG_HOME` | Explicit OpenCode XDG config root | Native OpenCode configuration authority |
| `BENCHMARK_OPENCODE_AGENT` | Exact OpenCode agent persona to execute | Native OpenCode agent authority |
| `BENCHMARK_PASSTHROUGH_ENV_KEYS` | Comma-separated host variable names explicitly admitted into participant processes | Optional provider environment authority |
| `BENCHMARK_SUITE_PATH` | Committed suite definition inside agentsCookbook | Benchmark source/configuration |
| `BENCHMARK_CAMPAIGN_ROOT` | Writable campaign directory containing `cache/`, `work/`, and `results/` | Generated campaign evidence |
| `BENCHMARK_HARNESS_REPO_ROOT` | agentsCookbook checkout containing the runner | Harness source authority |
| `BENCHMARK_SCORE_SCRIPT_PATH` | Optional suite-specific scorer | Specialized reporting authority |
| `BENCHMARK_SCORE_OUTPUT_PATH` | Output file for the suite-specific score | Generated report |

A **suite path is not an output directory**. A **campaign root is not source configuration**. A native agent's config root is not subject executable authority. These distinctions are enforced so one configured authority cannot silently stand in for another.

For local human-driven campaigns:

```sh
cp -n .env.example .env
# edit .env and set the authorities used by the selected suite
```

Then use:

```sh
make benchmark-check
make benchmark
make benchmark-report    # generic framework report
make benchmark-score     # suite-specific scorer configured in .env
```

The Makefile chooses no suite, campaign path, harness path, product executable, native config root, provider environment, agent persona, or specialized scorer. Missing authority fails before benchmark work begins.

### Advanced direct CLI

The Python CLI remains available for automation and explicit one-off selections. It does not discover `.env` and does not default `--harness-root`.

For example:

```bash
python -m benchmarks preflight \
  --env-file .env \
  --suite "$BENCHMARK_SUITE_PATH" \
  --root "$BENCHMARK_CAMPAIGN_ROOT" \
  --harness-root "$BENCHMARK_HARNESS_REPO_ROOT" \
  --agent opencode-native \
  --subject hashmarks \
  --subject none
```

Selecting `--subject hashmarks` selects only Hashmarks conditions. If a paired bare control is wanted, request `--subject none` explicitly; the selection layer never adds controls implicitly.

Then run the exact same explicit selection:

```bash
python -m benchmarks run \
  --env-file .env \
  --suite "$BENCHMARK_SUITE_PATH" \
  --root "$BENCHMARK_CAMPAIGN_ROOT" \
  --harness-root "$BENCHMARK_HARNESS_REPO_ROOT" \
  --agent opencode-native \
  --subject hashmarks \
  --subject none
```

Status and report do not execute participants, so they need only the suite, campaign results, and the same explicit selection:

```bash
python -m benchmarks status \
  --suite "$BENCHMARK_SUITE_PATH" \
  --root "$BENCHMARK_CAMPAIGN_ROOT" \
  --agent opencode-native \
  --subject hashmarks \
  --subject none

python -m benchmarks report \
  --suite "$BENCHMARK_SUITE_PATH" \
  --root "$BENCHMARK_CAMPAIGN_ROOT" \
  --agent opencode-native \
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
python -m benchmarks run \
  --suite "$suite" \
  --root "$root" \
  --agent opencode-native \
  --subject hashmarks \
  --subject enola
```

The runner reuses valid existing receipts, so rerunning the command resumes a partially completed campaign instead of starting completed definitions again.

Inspect resumability without invoking any agent:

```bash
python -m benchmarks status \
  --suite "$suite" \
  --root "$root" \
  --agent opencode-native \
  --subject hashmarks \
  --subject enola
```

`status.complete` means every selected definition has a verified immutable receipt. `status.qualified` additionally requires every receipt to be a valid experimental outcome (`PASS`, `FAIL`, or `NO_QUALIFYING_DEFECT`). A campaign can therefore be structurally complete but not qualified.

Finally:

```bash
python -m benchmarks report \
  --suite "$suite" \
  --root "$root" \
  --agent opencode-native \
  --subject hashmarks \
  --subject enola
```

The same selectors should be used across preflight, run, status, and report. Bare controls are included only when explicitly selected or when the full frozen suite is run without subject filters.

### Immutable non-outcome receipts

A published `INCOMPLETE`, `INVALID`, or `CONTAMINATED` receipt is evidence and is never deleted or silently overwritten. If the underlying infrastructure problem is corrected but observed execution authority does not change, start a new campaign root instead of mutating the old evidence. If observed tool/config authority changes, execution identity changes naturally and the new execution can coexist.

`--root` is only path derivation for `cache/`, `work/`, and `results/`; it does not create a second mutable campaign manifest. Frozen suite definitions plus verified receipts remain authority.

## Method

Fresh authority -> frozen input -> preflight admission -> isolated execution -> observed execution identity -> independent oracle -> sealed events -> immutable verified receipt -> status/resume -> aggregate only valid evidence.

Do not change a frozen task, mutation, oracle, or scoring contract after seeing a result. Create a new suite/experiment version instead.
