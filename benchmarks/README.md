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

Native tool discovery and benchmark-subject selection are separate authorities.

Codex, OpenCode, and Enola are normal host-installed tools. The benchmark does not duplicate their standard Linux installation paths or config roots in `.env`. It resolves their executables from the native `PATH`, derives Codex/OpenCode config roots from the host's normal `HOME`, `XDG_CONFIG_HOME`, and `CODEX_HOME` conventions, then records the resolved executable hash, version, native config identity, and effective subject exposure. Native defaults are therefore **observed authority**, not hidden benchmark configuration.

Hashmarks is intentionally different: it is the locally developed product under test, so `HASHMARKS_BENCH_SOURCE` explicitly selects the clean committed checkout and its exact `.venv/bin/hashmarks`. This prevents an unrelated installed Hashmarks from silently replacing the candidate under test.

For native OpenCode and Codex trials, ambient/global MCP registrations are disabled as subject authority. The selected Hashmarks or Enola subject is injected ephemerally from the adapter-owned exact executable/cwd/args. A global MCP registration can therefore exist for normal development without choosing what the benchmark executes.

Participant processes do not inherit arbitrary host environment variables. The harness carries one fixed process-substrate allowlist—`PATH`, locale variables, terminal identity, and equivalent Windows launch variables—so native tools can start. Provider variables must be named explicitly through `BENCHMARK_PASSTHROUGH_ENV_KEYS`. The resulting observed environment is bound into execution identity.

There is no automatic `.env` discovery in the benchmark CLI and no default harness root. Local Make targets pass `--env-file .env`, `--suite`, `--root`, and `--harness-root` explicitly. Direct CLI callers must provide the same authorities themselves.

Agent Economics remains a benchmark consumer/suite; shared process semantics remain single-owned until that module is promoted to a more generic repository location.

## Recommended campaign workflow

### Authority vocabulary

Keep deliberate benchmark choices separate from native host discovery:

| Setting | Meaning | Authority/lifetime |
| --- | --- | --- |
| `HASHMARKS_BENCH_SOURCE` | Clean committed Hashmarks checkout being measured | Explicit product source authority |
| `BENCHMARK_OPENCODE_AGENT` | Exact OpenCode agent persona to execute | Explicit benchmark semantic choice |
| `BENCHMARK_PASSTHROUGH_ENV_KEYS` | Comma-separated provider variables explicitly admitted into participant processes | Optional provider environment authority |
| `BENCHMARK_SUITE_PATH` | Committed suite definition inside agentsCookbook | Benchmark source/configuration |
| `BENCHMARK_CAMPAIGN_ROOT` | Writable campaign directory containing `cache/`, `work/`, and `results/` | Generated campaign evidence |
| `BENCHMARK_HARNESS_REPO_ROOT` | agentsCookbook checkout containing the runner | Harness source authority |
| `BENCHMARK_SCORE_SCRIPT_PATH` | Optional suite-specific scorer | Specialized reporting authority |
| `BENCHMARK_SCORE_OUTPUT_PATH` | Output file for the suite-specific score | Generated report |

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

Then use:

```sh
make benchmark-check
make benchmark
make benchmark-report    # generic framework report
make benchmark-score     # suite-specific scorer configured in .env
```

The Makefile chooses no native executable or native config root. Codex, OpenCode, and Enola use their installed host conventions; the benchmark observes what resolves. The Makefile only transports deliberate benchmark choices such as the Hashmarks checkout, suite, campaign root, OpenCode agent persona, provider passthrough, and scorer. Missing explicit benchmark choices fail before work begins.

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
