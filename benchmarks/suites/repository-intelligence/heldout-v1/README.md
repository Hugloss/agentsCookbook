# Held-out repository observer outcomes v1

This agentsCookbook suite measures what native Codex and native OpenCode do with bare tools, Hashmarks MCP, or Enola MCP. It contains twelve pinned tasks: five Python localization tasks on Hashmarks, one Python defect repair on agentsCookbook, and six TypeScript localization tasks on UV Fleet. Each of six agent/subject conditions runs three paired seeds per task: 216 trials. The source commits predate this suite, so task answers are absent from each trial repository.

**Status:** heldout-v1 is still being qualified. Its repository/source pins are deliberate, but the benchmark is not considered frozen until its oracle semantics and a complete campaign are qualified. Benchmark defects found during qualification are repaired in v1; results produced under superseded v1 authority must not be mixed with current score projections. Once v1 is frozen, newly discovered benchmark ideas enter as diagnostic/shadow tasks first rather than being added post-hoc to the scored population.

The runner owns process execution, isolation, contamination checks, receipts, and scoring. Hashmarks supplies repository evidence only. Localization tasks use a deterministic repository-location oracle; the repair task keeps its independent command oracle. Expected answers and repair checks live in the suite definitions and are never supplied to the agent prompt.

### Localization grading

Localization PASS/FAIL measures whether the agent identified the frozen repository location. Instruction-format compliance remains separately observable.

The repository-location oracle accepts only:

- one bare JSON object, or one `json` fenced JSON object, with exactly `path` and `symbol`
- a repository-relative path, or an absolute path that resolves inside the isolated trial workspace
- an unqualified symbol or a qualified callable name whose terminal symbol identifies the same target

It never extracts JSON from surrounding prose, never chooses among multiple objects, and rejects paths escaping the trial workspace. A single JSON fence is semantically gradeable but records `format_compliant=false`; the task prompt still requires a bare JSON object. Qualified symbols such as `WorkspaceMapStore.paths_under` normalize to `paths_under` for localization comparison without weakening the expected repository target.

The localization boundary is deliberately split into observation and scoring. `repository-location-normalization.v1` parses and normalizes the frozen agent answer without deciding correctness. `repository-location-score.v1` compares that observation with frozen oracle truth. The resulting semantic status is `CORRECT`, `INCORRECT`, or `UNSCORABLE`; an unscorable answer is not silently relabeled as a proven wrong location.

The result receipt keeps execution evidence separate from the score projection. `execution.evidence_identity` binds the frozen task execution, runtime authorities, mutation, environment, agent answer, and original workspace root without depending on oracle/scoring authority. `scoring.projection_identity` binds that execution evidence to the declared oracle and scoring policy. This permits deterministic offline repository-location regrading without another model run when only scoring authority changes.

Reports expose `semantic_success_rate`, `semantic_gradeable_rate`, semantic-status counts, and `format_compliance_rate` independently. Missing observations remain unknown with a zero denominator and a null rate; they are never converted to zero performance. Task PASS for localization follows semantic success; formatting remains a separate instruction-following signal.

A complete campaign with legitimate candidate FAIL outcomes can still be qualified evidence. Campaign qualification is lost by missing, incomplete, invalid, or contaminated execution evidence, not by the candidate simply answering incorrectly.

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
| `BENCHMARK_CAMPAIGN_ROOT` | Writable runtime/output directory for one campaign |
| `BENCHMARK_HARNESS_REPO_ROOT` | agentsCookbook checkout owning the benchmark runner |
| `BENCHMARK_SCORE_SCRIPT_PATH` | This suite's specialized scorer |
| `BENCHMARK_SCORE_OUTPUT_PATH` | Output path for the specialized held-out score |

```text
agentsCookbook/
└── benchmarks/suites/.../heldout-v1    <- BENCHMARK_SUITE_PATH
                                           committed definition; never campaign output

/tmp/agentscookbook-heldout-v1/          <- BENCHMARK_CAMPAIGN_ROOT
├── cache/
├── work/
└── results/
                                           generated campaign state/evidence
```

### Normal local workflow

Readiness needs no `BENCHMARK_AGENT`. Before preflight, execution, reporting, or scoring, select one or both agents explicitly in `.env`:

```dotenv
BENCHMARK_AGENT=opencode-native
# Or: BENCHMARK_AGENT=codex-native,opencode-native
```

If `BENCHMARK_AGENT` is absent or empty, selected-agent targets stop before any preflight or agent run.

```sh
make benchmark-check
# Optional explicit exhaustive admission:
make benchmark-check-all
make benchmark
make benchmark-report
make benchmark-score
```

- `benchmark-check` tests all six distinct agent/subject pairs once: each agent with bare tools, Hashmarks, and Enola. It uses one disposable smoke workspace, invokes no model, creates no trial, and exits.
- `benchmark-check-all` preflights 108 frozen definitions for one selected agent or 216 for both. It can be slow and is never run implicitly.
- `benchmark` executes/resumes the frozen campaign and does not secretly run either check first.
- `benchmark-report` is the generic framework report.
- `benchmark-score` runs this suite's explicit language-separated held-out scorer.
- Before a new full campaign after benchmark-authority changes, run `make benchmark-qualify-localization`. It exercises the four localization cases that exposed the v1 oracle defect across bare, Hashmarks, and Enola using a separate `/tmp/agentscookbook-heldout-v1-localization-qualification` campaign root. It is qualification evidence, not the full score.

The Makefile passes `.env` to the benchmark CLI, whose single configuration loader validates required settings. Native-installed tool paths are intentionally delegated to Linux/tool discovery and then recorded as observed authority.

Do not run `hashmarks install --opencode` for benchmark authority and do not prepend the local Hashmarks checkout to `PATH`. Enola should be installed normally (for example with its official installer) so `command -v enola` resolves it. Codex and OpenCode likewise use their normal installed commands. Global MCP registrations may exist for everyday development, but the benchmark does not use them to choose the subject executable.

### Advanced direct CLI

Most developers should use the Make targets. For direct CLI calls, the selected `.env` supplies benchmark choices; these shell variables are optional explicit overrides:

```sh
suite=benchmarks/suites/repository-intelligence/heldout-v1
root=/tmp/agentscookbook-heldout-v1
agents=opencode-native  # or codex-native,opencode-native
```

The fast readiness check needs only the suite and explicit env file:

```sh
uv run --no-project python -m benchmarks check \
  --env-file .env \
  --suite "$suite"
```

It does not need a campaign root, harness root, or agent selection. It verifies Hashmarks/Enola runtime availability, Codex/OpenCode native configuration, Codex exact subject exposure, and live OpenCode MCP connections. It does not make an LLM request. Add `--agent "$agents"` for a focused readiness check.

For exhaustive trial admission, pass campaign and harness authority explicitly:

```sh
uv run --no-project python -m benchmarks preflight \
  --env-file .env \
  --suite "$suite" \
  --root "$root" \
  --harness-root . \
  --agent "$agents"

uv run --no-project python -m benchmarks run \
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

Use a fresh campaign root for each independent Hashmarks candidate, native agent/model configuration, or benchmark-authority revision. Do not resume a campaign created before a task/oracle/scoring change even when the directory is still named heldout-v1. A failed preflight or incomplete receipt is not a scored trial. The specialized score writes one report for the selected population: 108 valid bundles for one agent or 216 for both, split evenly between Python and TypeScript. Its v2 JSON records `selection.agents` as a list. It compares assistance within each agent and reports cross-agent observations descriptively when both are selected. It does not rank the products into one winner.

The permanent drift gate lives in Hashmarks tests. This suite measures downstream agent behavior and must not replace Hashmarks' owner, ambiguity, provenance, freshness, or verification regressions.
