# Repository Intelligence

This suite measures repository-intelligence correctness and its effect on coding-agent
work without making any evaluated product its own grading authority.

Hashmarks and Enola keep their native CLI/MCP semantics. The benchmark does not ETL
their facts into a shared repository graph. Only the experiment envelope is normalized:
participant identity, tool exposure/adoption, execution evidence, budgets,
contamination, independent grading, receipts, and reporting.

## pilot-v1

`pilot-v1/` is the first executable harness qualification. It freezes three tasks on
one exact agentsCookbook commit/tree and compares bare, Hashmarks, and Enola using the
Codex host-default model.

It remains immutable historical evidence.

## agent-matrix-v2

`agent-matrix-v2/` freezes a new experiment version on the merged pilot
implementation bytes. It keeps the same three task families and expands to two agent
runtime authorities:

- Codex with explicit `gpt-5.6-sol` / high reasoning;
- native OpenCode using the host's already configured provider/model/auth.

Each runtime runs bare, with Hashmarks, and with Enola, producing 18 frozen definitions.

**Gemma is never routed through Codex.** When native OpenCode is configured to Gemma,
the benchmark uses that native setup and observes/binds what actually ran. No
OpenCode model/provider configuration is stored in this repository.

The benchmark composes a transient OpenCode runtime overlay while preserving the
host's native model, provider, authentication, permissions, and existing inline
configuration. Bare trials disable repository-intelligence MCP servers. Assisted
trials take the selected subject's MCP exposure from its benchmark adapter: the exact
admitted Hashmarks or Enola executable, arguments, working directory, and isolated
state/config needed for that trial. Any same-named project/global OpenCode MCP entry is
observed but shadowed for the trial; it is not benchmark subject authority.

Native OpenCode assistance is admitted only when that benchmark-owned subject exposure
can be proven to target the isolated trial workspace and the effective OpenCode MCP
command resolves to the admitted executable identity. Hashmarks is proven from its
explicit `--workspace`; Enola is proven from its explicit trial repository/config
binding. Missing executables, changed exposure identity, or unprovable/outside-workspace
bindings produce `INCOMPLETE` before agent work.

Primary interpretation is assistance gain within the same runtime/model authority.
Cross-runtime rows are descriptive only.

## Measurement boundary

The suites measure correctness, subject availability, MCP configuration/adoption,
command/tool calls, MCP evidence bytes when observable, token usage when exposed,
duration, contamination, and oracle health.

The native agent event surfaces do not authoritatively expose repository file-read
bytes, so the suites explicitly mark that archaeology metric unavailable rather than
estimating it.
OpenCode Code Mode child calls are counted from export metadata when present. Per-child
result bytes and calls without usable metadata remain unobserved.

Do not publish an overall winner score.

## Current native suites

`multidomain-v2/` is an explicit draft benchmark with 60 frozen evidence cases
and 36 agent tasks covering logs, Splunk CSV, dependencies, semantics, identities,
and code ownership across four pinned repositories. Its new questions and oracles
await independent review; the reports disclose that state. It is never invoked
by Hashmarks release or ordinary test workflows. See its README for exact commands.

`native-matrix-v3/` is the current native Codex/OpenCode comparison, with one paired smoke task by default from Hashmarks. It pins a source revision without checked-in answers. `enola-cycle-reproduction-v1/` adapts the published TypeScript cycle example and reports functional success and cycle introduction separately. Both are development-only experiments in agentsCookbook; neither enters the installed Hashmarks product.

## headroom-v1

`headroom-v1/` is a diagnostic-only repeated paired suite created after heldout-v1
campaign 000006 exposed a bare-control ceiling. It reuses four harder behavioral-v4
case/oracle authorities (change impact, freshness, declarations, and verification)
with three replicates per bare/Hashmarks/Enola condition. It explicitly reports whether
bare-control headroom was actually observed; it does not assume assistance benefit,
replace heldout-v1, or carry release authority.

See `headroom-v1/README.md` for its isolated config and commands.

## Required-tool diagnostics after heldout-v1 run 000007

Run 000007 completed 108 receipts but did not qualify: Enola was never called, and
Hashmarks was called in 7 of its 36 assisted trials. Its gradeable location answers
also used JSON fences even though the prompts requested one plain JSON object. The
ordinary paired suite remains the natural-use measure. The separate tool probes below
ask what happens after a specific subject tool is required; they are diagnostic only.

Prepare one 9-trial suite per subject from the reviewed heldout task and oracle bytes:

```bash
python3 -m benchmarks tool-probe-prepare \
  --suite benchmarks/suites/repository-intelligence/heldout-v1 \
  --subject hashmarks --output-suite /tmp/hashmarks-required-tool-probe
python3 -m benchmarks tool-probe-prepare \
  --suite benchmarks/suites/repository-intelligence/heldout-v1 \
  --subject enola --output-suite /tmp/enola-required-tool-probe
```

Each generated suite contains `.env.example` and `score.py`. Copy the example config,
set the exact Hashmarks source for its suite, and complete the independent oracle
reviews required after the task prompts change. When OpenCode is available, use
`benchmarks oracle-review --suite <generated-suite> --execute`, followed by
`benchmarks oracle-review-check --suite <generated-suite> --require-complete`. Then
run `benchmarks check --env-file <copied-env>`, `benchmarks run --new --env-file
<copied-env>`, and `benchmarks score --env-file <copied-env>` separately for each
subject. Run from this repository root. The generated score records a completed
required call with nonempty output, an attempted call that failed, an observed trace
without the call, or an unavailable trace independently of semantic correctness.

Every completed report now writes `trace-diagnostics.json`, a derived view of sealed
traces with per-call order, status, failure category, input hash, file path attempts,
and Hashmarks returned-candidate target rank. It reports absent or unsupported traces
as unknown. To inspect an older campaign without rewriting its historical reports:

```bash
python3 -m benchmarks trace-diagnostics \
  --results .benchmark-runs/heldout-v1/runs/000007/results \
  --output .benchmark-runs/heldout-v1/runs/000007/reports/trace-diagnostics-retro.json
```

For an observed Hashmarks query, `hashmarks-retrieval-probe` replays its exact text
against a specified checkout and executable at limits 20 and 50, then checks whether
exact symbol search can find the frozen oracle target. This is candidate evidence;
its output does not claim a product defect or comparability across repository
revisions.

Run 000007's pinned repository replay is saved as
`reports/hashmarks-retrieval-probe-retro.json`. It used the currently installed
Hashmarks executable against the task's pinned repository checkout, so the repository
revision matches while the executable's implementation remains a separate recorded
identity.

## behavioral-v3

`behavioral-v3/` adds independent agent-outcome challenges for post-edit refresh,
change impact, focused verification, and dependency-delta semantics. Its edit tasks
start with the subject prepared against the frozen synthetic mini-project and then let
the agent change only the declared owner path, so post-change behavior is exercised
without copying Hashmarks unit tests into the benchmark. It is research-only and has
no release authority.
