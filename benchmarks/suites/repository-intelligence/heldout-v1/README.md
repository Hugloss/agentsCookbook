# Held-out repository observer outcomes v1

This agentsCookbook suite measures what native Codex and native OpenCode do with bare tools, Hashmarks MCP, or Enola MCP. It contains twelve pinned tasks: five Python localization tasks on Hashmarks, one Python defect repair on agentsCookbook, and six TypeScript localization tasks on UV Fleet. Each of six agent/subject conditions runs three paired seeds per task: 216 frozen trials. The source commits predate this suite, so task answers are absent from each trial repository.

The runner owns process execution, isolation, contamination checks, receipts, and scoring. Hashmarks supplies repository evidence only. Expected JSON answers and the repair oracle live in the suite definitions and are never supplied to the agent prompt. The repair mutation and its focused test come from the already validated native matrix v3.

From the agentsCookbook root, bind the Hashmarks checkout under test:

```sh
export HASHMARKS_BENCH_SOURCE=/absolute/path/to/Hashmarks
```

Do not run `hashmarks install --opencode` for the benchmark and do not prepend the checkout to `PATH`. The source must be a clean committed checkout. The harness directly selects `$HASHMARKS_BENCH_SOURCE/.venv/bin/hashmarks`, records its Git commit/tree, and injects that exact executable into the ephemeral OpenCode benchmark exposure. Repository-local `opencode.json` is not created or modified.

Then validate and preflight:

```sh
python -m benchmarks validate-suite --suite benchmarks/suites/repository-intelligence/heldout-v1
python -m benchmarks plan --suite benchmarks/suites/repository-intelligence/heldout-v1
python -m benchmarks preflight --suite benchmarks/suites/repository-intelligence/heldout-v1 --root /path/to/new/campaign --harness-root .
python -m benchmarks run --suite benchmarks/suites/repository-intelligence/heldout-v1 --root /path/to/new/campaign --harness-root .
python benchmarks/suites/repository-intelligence/heldout-v1/score.py --results /path/to/new/campaign/results --output /path/to/new/campaign/heldout-report.json
```

Use a fresh campaign root for each Hashmarks candidate and native agent/model configuration. The selected Hashmarks executable must be bound to the checkout under test. Native Codex requires enabled Hashmarks and Enola MCP registrations; native OpenCode requires a resolvable model/provider configuration. The existing native matrix v3 README documents subject registration and authentication preflight. A failed preflight or incomplete receipt is not a scored trial. The score script requires all 216 valid bundles and reports Python and TypeScript separately, with within-agent paired assistance and descriptive cross-agent observations. It does not rank the products into one winner.

The permanent drift gate lives in Hashmarks tests. This suite measures downstream agent behavior and must not replace Hashmarks' owner, ambiguity, provenance, freshness, or verification regressions.
