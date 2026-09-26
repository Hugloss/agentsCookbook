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

Agent Economics remains a benchmark consumer/suite; shared process semantics remain single-owned until that module is promoted to a more generic repository location.

## Recommended campaign workflow

Use one external campaign root to avoid repeating cache/work/results paths:

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
