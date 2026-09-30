# Held-out repository observer outcomes v1

This agentsCookbook suite measures what native Codex and native OpenCode do with bare tools, Hashmarks MCP, or Enola MCP. It contains twelve pinned tasks: five Python localization tasks on Hashmarks, one Python defect repair on agentsCookbook, and six TypeScript localization tasks on UV Fleet. Each of six agent/subject conditions runs three paired seeds per task: 216 frozen trials. The source commits predate this suite, so task answers are absent from each trial repository.

The runner owns process execution, isolation, contamination checks, receipts, and scoring. Hashmarks supplies repository evidence only. Expected JSON answers and the repair oracle live in the suite definitions and are never supplied to the agent prompt. The repair mutation and its focused test come from the already validated native matrix v3.

From the agentsCookbook root, configure the benchmark authority once:

```sh
cp -n .env.example .env
# edit .env
```

### What the local settings mean

The held-out suite uses four different authority groups.

**Products being measured**

| Setting | What it points to |
| --- | --- |
| `HASHMARKS_BENCH_SOURCE` | Clean committed Hashmarks checkout; the benchmark executes its exact `.venv/bin/hashmarks` |
| `ENOLA_BENCH_EXECUTABLE` | Exact Enola executable; no PATH fallback |

**Native agents**

| Setting | What it points to |
| --- | --- |
| `BENCHMARK_CODEX_EXECUTABLE` | Exact Codex executable |
| `BENCHMARK_CODEX_HOME` | Codex model/auth configuration root |
| `BENCHMARK_OPENCODE_EXECUTABLE` | Exact OpenCode executable |
| `BENCHMARK_OPENCODE_HOME` | OpenCode home |
| `BENCHMARK_OPENCODE_CONFIG_HOME` | OpenCode XDG configuration root |
| `BENCHMARK_OPENCODE_AGENT` | Exact OpenCode agent persona, such as `build` |

The benchmark does **not** trust global Hashmarks/Enola MCP registrations in Codex or OpenCode as subject authority. Ambient MCP servers are disabled for the trial and the selected subject is injected ephemerally from the exact product authority above.

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

```sh
make benchmark-check
make benchmark
make benchmark-report
make benchmark-score
```

- `benchmark-check` performs admission/preflight without invoking the coding agent.
- `benchmark` executes/resumes the frozen campaign.
- `benchmark-report` is the generic framework report.
- `benchmark-score` runs this suite's explicit language-separated held-out scorer.

The Makefile provides no hidden fallback values for these authorities.

Do not run `hashmarks install --opencode` for this benchmark and do not prepend Hashmarks or Enola to `PATH`. Native Codex also does not need a global Hashmarks or Enola MCP registration for benchmark subject execution. The selected subject exposure is injected for the trial and bound to the exact executable.

### Advanced direct CLI

Most developers should use the Make targets. Direct callers must pass the env file and harness root explicitly:

```sh
python -m benchmarks preflight \
  --env-file .env \
  --suite "$BENCHMARK_SUITE_PATH" \
  --root "$BENCHMARK_CAMPAIGN_ROOT" \
  --harness-root "$BENCHMARK_HARNESS_REPO_ROOT"

python -m benchmarks run \
  --env-file .env \
  --suite "$BENCHMARK_SUITE_PATH" \
  --root "$BENCHMARK_CAMPAIGN_ROOT" \
  --harness-root "$BENCHMARK_HARNESS_REPO_ROOT"
```

When filtering subjects, controls are never added automatically. For a Hashmarks-vs-bare paired subset, request both explicitly:

```sh
python -m benchmarks preflight \
  --env-file .env \
  --suite "$BENCHMARK_SUITE_PATH" \
  --root "$BENCHMARK_CAMPAIGN_ROOT" \
  --harness-root "$BENCHMARK_HARNESS_REPO_ROOT" \
  --agent opencode-native \
  --subject hashmarks \
  --subject none
```

Use a fresh campaign root for each independent Hashmarks candidate or native agent/model configuration. A failed preflight or incomplete receipt is not a scored trial. The specialized score requires all 216 valid bundles and reports Python and TypeScript separately, with within-agent paired assistance and descriptive cross-agent observations. It does not rank the products into one winner.

The permanent drift gate lives in Hashmarks tests. This suite measures downstream agent behavior and must not replace Hashmarks' owner, ambiguity, provenance, freshness, or verification regressions.
