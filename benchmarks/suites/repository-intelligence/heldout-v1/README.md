# Held-out repository observer outcomes v1

This agentsCookbook suite measures what native Codex and native OpenCode do with bare tools, Hashmarks MCP, or Enola MCP. It contains twelve pinned tasks: five Python localization tasks on Hashmarks, one Python defect repair on agentsCookbook, and six TypeScript localization tasks on UV Fleet. Each of six agent/subject conditions runs three paired seeds per task: 216 frozen trials. The source commits predate this suite, so task answers are absent from each trial repository.

The runner owns process execution, isolation, contamination checks, receipts, and scoring. Hashmarks supplies repository evidence only. Expected JSON answers and the repair oracle live in the suite definitions and are never supplied to the agent prompt. The repair mutation and its focused test come from the already validated native matrix v3.

From the agentsCookbook root, configure the benchmark authority once:

```sh
cp -n .env.example .env
# edit .env
```

The four local settings deliberately name different things:

| Setting | What it points to | Example |
| --- | --- | --- |
| `HASHMARKS_BENCH_SOURCE` | The clean committed **Hashmarks checkout being measured** | `/home/me/code/Hashmarks` |
| `BENCHMARK_SUITE_PATH` | The committed **benchmark definition inside agentsCookbook** | `benchmarks/suites/repository-intelligence/heldout-v1` |
| `BENCHMARK_CAMPAIGN_ROOT` | The writable **runtime/output directory for one campaign** | `/tmp/agentscookbook-heldout-v1` |
| `BENCHMARK_HARNESS_REPO_ROOT` | The **agentsCookbook checkout** that owns the runner | `.` when running from the repository root |

In particular:

```text
agentsCookbook/
└── benchmarks/suites/.../heldout-v1    <- BENCHMARK_SUITE_PATH
                                           committed definition; do not write results here

/tmp/agentscookbook-heldout-v1/          <- BENCHMARK_CAMPAIGN_ROOT
├── cache/
├── work/
└── results/
                                           generated campaign state/evidence
```

A suite path answers **"what benchmark definition are we running?"**. A campaign root answers **"where does this run store generated work and evidence?"**. They are intentionally different authorities.

`.env` is ignored by Git. The normal local workflow is only:

```sh
make benchmark-check
make benchmark
make benchmark-report
```

The Makefile provides no hidden fallback values for the product checkout, suite path, campaign root, or harness repository root. If a required value is absent, the command fails before benchmark execution.

Do not run `hashmarks install --opencode` for the benchmark and do not prepend the checkout to `PATH`. The source must be a clean committed checkout. The harness directly selects `$HASHMARKS_BENCH_SOURCE/.venv/bin/hashmarks`, records its Git commit/tree, and injects that exact executable into the ephemeral OpenCode benchmark exposure. Repository-local `opencode.json` is not created or modified.

### Advanced direct CLI

The Python CLI is the underlying execution interface for automation and one-off selections. Most developers should use the Make targets above. When invoking the CLI directly, pass the same authorities explicitly rather than inventing alternate defaults.

Use a fresh campaign root for each Hashmarks candidate and native agent/model configuration. The selected Hashmarks executable must be bound to the checkout under test. Native Codex requires enabled Hashmarks and Enola MCP registrations; native OpenCode requires a resolvable model/provider configuration. The existing native matrix v3 README documents subject registration and authentication preflight. A failed preflight or incomplete receipt is not a scored trial. The score script requires all 216 valid bundles and reports Python and TypeScript separately, with within-agent paired assistance and descriptive cross-agent observations. It does not rank the products into one winner.

The permanent drift gate lives in Hashmarks tests. This suite measures downstream agent behavior and must not replace Hashmarks' owner, ambiguity, provenance, freshness, or verification regressions.
