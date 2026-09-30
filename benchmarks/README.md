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

For native OpenCode trials, OpenCode remains the authority for model, provider, authentication, permissions, and user configuration. The selected benchmark subject is different authority: its adapter supplies the exact MCP executable and invocation. The harness overlays only that subject exposure and tool gating through OpenCode's native runtime configuration, proves the effective executable/workspace binding before agent work, and binds the exposure digest into execution authority. A repository-local OpenCode MCP entry may therefore be observed and shadowed for the trial, but it never chooses which Hashmarks or Enola executable is benchmarked.

The benchmark never creates or edits repository-local `opencode.json` to register a subject, and an ambient/global Hashmarks MCP registration is never benchmark execution authority. For source-bound Hashmarks runs, `HASHMARKS_BENCH_SOURCE` directly selects that checkout's `.venv/bin/hashmarks`; changing `PATH` is neither required nor authoritative.

For local runs, copy `.env.example` to the ignored `.env` file and set `HASHMARKS_BENCH_SOURCE` there. `preflight` and `run` load only that benchmark-owned variable from `.env` by default; use `--env-file PATH` for another file. An already exported process value takes precedence. Every selected Hashmarks benchmark condition requires this source authority and fails before trial admission if the value is still missing.

Agent Economics remains a benchmark consumer/suite; shared process semantics remain single-owned until that module is promoted to a more generic repository location.

## Recommended campaign workflow

For local human-driven campaigns, configure authority once:

```sh
cp -n .env.example .env
# edit .env and set:
# HASHMARKS_BENCH_SOURCE=...
# BENCHMARK_SUITE=...
# BENCHMARK_ROOT=...
# BENCHMARK_HARNESS_ROOT=...
```

Then use the thin Make entrypoints:

```sh
make benchmark-check
make benchmark
make benchmark-report
```

The Makefile has no fallback suite, campaign root, harness root, or Hashmarks checkout. It only transports the explicit values from `.env` and fails before benchmark execution when any required value is absent.

The underlying CLI remains available for automation and explicit one-off selections. Use one external campaign root to avoid repeating cache/work/results paths:

```bash
suite="benchmarks/suites/repository-intelligence/agent-matrix-v2"
root="${TMPDIR:-/tmp}/ri-live"

python -m benchmarks preflight \
  --suite "$suite" \
  --root "$root" \
  --agent opencode-native \
  --subject hashmarks \
  --subject enola
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

The same selectors should be used across preflight, run, status, and report. Assisted subject selection automatically includes the matching bare control.

### Immutable non-outcome receipts

A published `INCOMPLETE`, `INVALID`, or `CONTAMINATED` receipt is evidence and is never deleted or silently overwritten. If the underlying infrastructure problem is corrected but observed execution authority does not change, start a new campaign root instead of mutating the old evidence. If observed tool/config authority changes, execution identity changes naturally and the new execution can coexist.

`--root` is only path derivation for `cache/`, `work/`, and `results/`; it does not create a second mutable campaign manifest. Frozen suite definitions plus verified receipts remain authority.

## Method

Fresh authority -> frozen input -> preflight admission -> isolated execution -> observed execution identity -> independent oracle -> sealed events -> immutable verified receipt -> status/resume -> aggregate only valid evidence.

Do not change a frozen task, mutation, oracle, or scoring contract after seeing a result. Create a new suite/experiment version instead.
