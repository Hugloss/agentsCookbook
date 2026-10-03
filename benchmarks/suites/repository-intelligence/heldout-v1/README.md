# Held-out repository observer outcomes v1

This agentsCookbook suite measures what native Codex and native OpenCode do with bare tools, Hashmarks MCP, or Enola MCP. It contains twelve pinned tasks: five Python localization tasks on Hashmarks, one Python defect repair on agentsCookbook, and six TypeScript localization tasks on UV Fleet. Each of six agent/subject conditions runs three paired replicates per task: 216 trials. The source commits predate this suite, so task answers are absent from each trial repository.

**Status:** heldout-v1 is still being qualified. Its repository/source pins are deliberate, but the benchmark is not considered frozen until its oracle semantics and a complete campaign are qualified. Benchmark defects found during qualification are repaired in v1; results produced under superseded v1 authority must not be mixed with current score projections. Once v1 is frozen, newly discovered benchmark ideas enter as diagnostic/shadow tasks first rather than being added post-hoc to the scored population.

The runner owns process execution, isolation, contamination checks, receipts, and scoring. Hashmarks supplies repository evidence only. Localization tasks use a deterministic repository-location oracle; the repair task keeps its independent command oracle. Expected answers and repair checks live in the suite definitions and are never supplied to the agent prompt.

### Localization grading

Localization PASS/FAIL measures whether the agent identified the frozen repository location. Instruction-format compliance remains separately observable.

The repository-location oracle accepts only:

- one bare JSON object, or one `json` fenced JSON object, with exactly `path` and `symbol`
- a repository-relative path, or an absolute path that resolves inside the isolated trial workspace
- an unqualified symbol or a qualified callable name whose terminal symbol identifies the same target

It never extracts JSON from surrounding prose, never chooses among multiple objects, rejects duplicate JSON keys, and rejects paths escaping the trial workspace. A single JSON fence is semantically gradeable but records `format_compliant=false`; the task prompt still requires a bare JSON object. Qualified symbols such as `WorkspaceMapStore.paths_under` normalize to `paths_under` for localization comparison without weakening the expected repository target.

The localization boundary is deliberately split into observation and scoring. `repository-location-normalization.v2` parses and normalizes the frozen agent answer without deciding correctness. `repository-location-score.v2` compares that observation with frozen oracle truth. The resulting semantic status is `CORRECT`, `INCORRECT`, or `UNSCORABLE`; an unscorable answer is not silently relabeled as a proven wrong location. The suite remains heldout-v1 while it is being qualified; these internal policy identifiers distinguish incompatible evidence.

The result receipt keeps execution evidence separate from the score projection. `execution.evidence_identity` binds the frozen task execution, runtime authorities, mutation, environment, exact agent answer, original workspace root, recorded location observation, and agent trace digest without depending on oracle/scoring authority. `scoring.projection_identity` binds that execution evidence to the declared oracle and scoring policy. Verified bundles can be regraded without another model run when only scoring truth or policy changes and the normalization policy is unchanged. Older bundles without this evidence must be rerun.

Reports expose `semantic_success_rate`, `semantic_gradeable_rate`, semantic-status counts, and `format_compliance_rate` independently over valid localization outcomes. Missing observations remain unknown with a zero denominator and a null rate; they are never converted to zero performance. Task PASS for localization follows semantic success; formatting remains a separate instruction-following signal.

A complete campaign with legitimate candidate FAIL outcomes can still be qualified evidence. Campaign qualification is lost by missing, incomplete, invalid, or contaminated execution evidence, not by the candidate simply answering incorrectly.

### Replicates and stability

The frozen condition field `replicate_ids` identifies paired stochastic observations. Native Codex/OpenCode adapters do not currently transport a provider/model RNG seed. Historical `seed` receipts remain readable but are not comparable to the new execution contract.

Repeated outcomes are evidence, not retries. Reports therefore expose stability per
task/agent/subject as `stable-correct`, `stable-incorrect`, `unstable`, or
`execution-unstable` or `not-gradeable`. An incomplete or invalid execution is never converted into a
semantic failure. Paired bare-to-assisted rows also classify each valid replicate as
`gain`, `preserved`, `unresolved`, or `regression`, so aggregate success rates
cannot hide an assisted regression.

### Assistance attribution

The assisted condition and actual subject use are separate evidence. A Hashmarks or Enola
condition proves that the subject was available to the native agent; it does not prove that
the agent invoked it. Therefore:

- `paired_assistance_summary` is the overall **condition effect** and intentionally includes
  both invoked and non-invoked assisted pairs;
- `subject_adoption` reports availability, configuration, observed invocation, and non-use;
- `paired_assistance_usage_summary` and the derived decision-evidence assistance funnel
  split outcome transitions by `invoked`, `not-invoked`, and `unknown`;
- a gain or regression on a `not-invoked` pair is condition variance and must not be
  attributed to the subject tool.

This keeps the natural benchmark unforced while separating the path
`availability -> adoption -> usefulness when invoked`.

The committed `qualification/oracle-reviews.json` binds each expected owner to its task digest and records independent source-audit evidence. One independent review with a `unique` decision is the default qualification requirement. A second independent review is required only when the task carries an explicit evidence-backed escalation reason, such as prior benchmark instability or unresolved ownership ambiguity. Campaign admission fails before any model call while any task lacks its required reviews or has a non-unique decision. If a task has two defensible owners, repair or retire it and start a new saved run; do not add a grading exception. Current heldout-v1 authority escalates `locate-prefix-path-enumerator`, `locate-directory-pruning`, and `locate-resource-invalidation` to two independent reviews because run 000007 exposed semantic instability on those task boundaries; both committed reviews independently retain the frozen owner as unique.

The campaign authority receipt freezes runtime and task inputs before inference. One launch claim is written before each model call; an interrupted claim is evidence and cannot be rerun in place. Reports expose execution, gradeability, semantic stability, output compliance, diagnostic boundaries, paired transitions, and excluded pairs separately. A diagnostic suite prepared with `diagnostic-prepare` has ten replicates per selected unstable task and its own root; its results never enter the official held-out score.

Native OpenCode project configuration can differ between pinned repositories. Campaign admission records it per task and condition, while requiring the executable, model, and provider to remain stable for each agent. Reports expose the task and agent config fingerprints, and paired conditions for one task must still match exactly.

After a qualified official score, prepare the diagnostic suite with:

```sh
uv run --no-project python -m benchmarks diagnostic-prepare \
  --suite benchmarks/suites/repository-intelligence/heldout-v1 \
  --score /path/to/qualified-heldout-score.json \
  --source-results /path/to/qualified-campaign/results \
  --output-suite /tmp/agentscookbook-heldout-diagnostic-v1 \
  --include-task locate-repository-content-identity
```

Run that generated suite with a distinct campaign root. Keep its report separate from the official score. Freeze heldout-v1 only after both selected native agents finish fresh qualified campaigns, every oracle review is complete, and remaining unstable results have an explicit owner; any later semantic change starts a new benchmark generation.

From the agentsCookbook root, configure the benchmark authority once:

```sh
cp -n .env.example .env
# edit .env
```

### What the local settings mean

The local file contains **benchmark choices**, not a mirror of Linux installation defaults.

**Explicit product choice**

| Setting | What it points to |
| --- | --- |
| `HASHMARKS_BENCH_SOURCE` | Clean committed Hashmarks checkout; the benchmark executes its exact `.venv/bin/hashmarks` |
| `BENCHMARK_AGENT` | One native agent or explicit comma-separated list, for example `codex-native,opencode-native`; there is no default for selected-agent work |

Hashmarks is explicit because we are actively developing it and may have several local checkouts/installations.

**Native-installed tools**

Enola, Codex, and OpenCode use their normal host installation/config conventions:

```text
command -v enola
command -v codex
command -v opencode
```

The benchmark resolves those commands through native `PATH`, fingerprints the executable actually found, and records its version. Codex config is discovered from native `CODEX_HOME` or `$HOME/.codex`; OpenCode uses native `HOME` and `XDG_CONFIG_HOME`/ `$HOME/.config`.

These paths are deliberately **not repeated in `.env`**. If the host's native installation changes, the observed execution identity changes.

`BENCHMARK_OPENCODE_AGENT` remains explicit because choosing `build` (or another persona) changes benchmark semantics; it is not a filesystem default.

Global Hashmarks/Enola MCP registrations in Codex/OpenCode are still not benchmark subject authority. Ambient MCP servers are disabled for the trial and the selected benchmark subject is injected ephemerally.

**Optional provider environment**

`BENCHMARK_PASSTHROUGH_ENV_KEYS` is a comma-separated allowlist of host environment variable names that a native provider needs, for example:

```dotenv
BENCHMARK_PASSTHROUGH_ENV_KEYS=OPENAI_API_KEY
```

Only named variables are transported. Participant processes do not otherwise inherit arbitrary host environment state. A declared passthrough variable that is unset causes admission to fail.

**Benchmark source and generated evidence**

| Setting | What it points to |
| --- | --- |
| `BENCHMARK_SUITE_PATH` | Committed benchmark definition inside agentsCookbook |
| `BENCHMARK_CAMPAIGN_ROOT` | Ignored store containing numbered saved runs |
| `BENCHMARK_HARNESS_REPO_ROOT` | agentsCookbook checkout owning the benchmark runner |
| `BENCHMARK_SCORE_SCRIPT_PATH` | This suite's specialized scorer |
| `BENCHMARK_SCORE_OUTPUT_PATH` | Score filename inside the selected saved run |

```text
agentsCookbook/
└── benchmarks/suites/.../heldout-v1    <- BENCHMARK_SUITE_PATH
                                           committed definition; never campaign output

.benchmark-runs/heldout-v1/              <- BENCHMARK_CAMPAIGN_ROOT
└── runs/000001/
    ├── cache/
    ├── work/
    ├── results/                        per-trial durable evidence
    └── heldout-report.json              derived score
```

### Normal local workflow

Readiness needs no `BENCHMARK_AGENT`. Before preflight, execution, reporting, or scoring, select one or both agents explicitly in `.env`:

```dotenv
BENCHMARK_AGENT=opencode-native
# Or: BENCHMARK_AGENT=codex-native,opencode-native
```

If `BENCHMARK_AGENT` is absent or empty, selected-agent targets stop before any preflight or agent run.

```sh
# Only runs if committed review policy says more evidence is required.
make benchmark-oracle-review
make benchmark-oracle-review-check
make benchmark-check
make benchmark-new
# Optional individual trial preflight:
make benchmark-check-all
make benchmark-resume
make benchmark-runs
make benchmark-report
make benchmark-score
```

- `benchmark-oracle-review` executes only reviews still required by the committed review-depth policy. It materializes the pinned target repository, invokes native OpenCode's read-only `plan` agent, withholds prior review rationale, and records the task-bound decision in `qualification/oracle-reviews.json`. Most tasks qualify after one independent source audit; evidence-escalated tasks alone incur the extra reviewer cost. It never runs benchmark trial models.
- `benchmark-oracle-review-check` is the fail-closed proof gate. If reviews are incomplete it prints the next Make command instead of leaving the user at a dead end.
- `benchmark-check` tests all six distinct agent/subject pairs once: each agent with bare tools, Hashmarks, and Enola. It uses one disposable smoke workspace, invokes no model, creates no trial, and exits.
- `benchmark-campaign-audit` observes every selected task/condition and checks cross-task runtime identity and paired input equivalence before inference. It publishes no campaign authority or launch claim. It reports `ready_for_campaign: false` and exits 2 while independent oracle reviews are pending; it cannot waive the run gate. Run it after changing the suite, runtime, or model selection and before a costly campaign.
- `benchmark-check-all` preflights 108 frozen definitions for one selected agent or 216 for both. It can be slow and is never run implicitly.
- `benchmark-new` saves a new numbered campaign without model calls; `benchmark-resume` executes or resumes the latest one. The plain `benchmark` target prints the required choice.
- `benchmark-report` is the generic framework report.
- `benchmark-score` runs this suite's explicit language-separated held-out scorer.
- Before a new full campaign after benchmark-authority changes, run `make benchmark-oracle-review-check` and `make benchmark-qualify-localization`. Do not buy a second review for every task by default: only tasks with recorded escalation evidence require it. The localization qualification then exercises five Python localization cases and one TypeScript case, including repository-content-identity, across bare, Hashmarks, and Enola for every selected agent. It is qualification evidence, not the full score.

For a scoring-only change to a complete campaign recorded under the current normalization and execution-evidence contracts, run offline scoring without editing the source bundles:

```sh
uv run --no-project python -m benchmarks regrade-score \
  --suite benchmarks/suites/repository-intelligence/heldout-v1 \
  --source-results /path/to/source-campaign/results \
  --agent opencode-native \
  --output /path/to/new-regraded-score.json
```

The offline report records source receipt hashes and projection identities. It rejects changed execution inputs, changed normalization policy, incomplete or invalid source trials, and a changed repair oracle. The output must be outside the source results directory.

The Makefile passes `.env` to the benchmark CLI, whose single configuration loader validates required settings. Native-installed tool paths are intentionally delegated to Linux/tool discovery and then recorded as observed authority.

Do not run `hashmarks install --opencode` for benchmark authority and do not prepend the local Hashmarks checkout to `PATH`. Enola should be installed normally (for example with its official installer) so `command -v enola` resolves it. Codex and OpenCode likewise use their normal installed commands. Global MCP registrations may exist for everyday development, but the benchmark does not use them to choose the subject executable.

### Advanced direct CLI

Most developers should use the Make targets. For direct CLI calls, the selected `.env` supplies benchmark choices; these shell variables are optional explicit overrides:

```sh
suite=benchmarks/suites/repository-intelligence/heldout-v1
root=.benchmark-runs/heldout-v1
agents=opencode-native  # or codex-native,opencode-native
```

The fast readiness check needs only the suite and explicit env file:

```sh
uv run --no-project python -m benchmarks check \
  --env-file .env \
  --suite "$suite"
```

It does not need a campaign root, harness root, or agent selection. It verifies Hashmarks/Enola runtime availability, Codex/OpenCode native configuration, Codex exact subject exposure, and live OpenCode MCP connections. It does not make an LLM request. Add `--agent "$agents"` for a focused readiness check.

Prepare a new saved run before exhaustive preflight:

```sh
uv run --no-project python -m benchmarks prepare --new --env-file .env
```

Then pass campaign and harness authority explicitly:

```sh
uv run --no-project python -m benchmarks campaign-audit \
  --env-file .env \
  --suite "$suite" \
  --root "$root" \
  --harness-root . \
  --agent "$agents"

uv run --no-project python -m benchmarks preflight \
  --env-file .env \
  --suite "$suite" \
  --root "$root" \
  --harness-root . \
  --agent "$agents"

uv run --no-project python -m benchmarks run \
  --resume \
  --env-file .env \
  --suite "$suite" \
  --root "$root" \
  --harness-root . \
  --agent "$agents"
```

When filtering subjects, controls are never added automatically. For a Hashmarks-vs-bare paired subset, request both explicitly:

```sh
uv run --no-project python -m benchmarks preflight \
  --env-file .env \
  --suite "$suite" \
  --root "$root" \
  --harness-root . \
  --agent "$agents" \
  --subject hashmarks \
  --subject none
```

Create a new numbered run for each independent Hashmarks candidate, native agent/model configuration, or benchmark-authority revision. Do not resume a run created before a task/oracle/scoring change. A failed preflight or incomplete receipt is not a scored trial. The specialized score writes a derived report inside the selected run: 108 valid bundles for one agent or 216 for both, split evenly between Python and TypeScript. Its JSON records `selection.agents` as a list. It compares assistance within each agent and reports cross-agent observations descriptively when both are selected. It does not rank the products into one winner.

The permanent drift gate lives in Hashmarks tests. This suite measures downstream agent behavior and must not replace Hashmarks' owner, ambiguity, provenance, freshness, or verification regressions.
