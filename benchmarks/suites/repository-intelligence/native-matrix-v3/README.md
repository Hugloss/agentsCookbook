# Native CLI matrix v3

Run from Hashmarks with `make benchmark` for the six-trial localization smoke, or `make benchmark BENCHMARK=matrix` for all 18 task/condition pairs. `BENCH_AGENT=codex-native` or `BENCH_AGENT=opencode-native` selects one native CLI and keeps all three subject arms. `make benchmark-show` prints the frozen definitions; `make benchmark-check` checks the selected native setup before any model call. Each run gets a fresh result directory; `make benchmark-report` reads its latest verified receipts, and `BENCH_RUN=<id>` selects a previous run.

The two CLI adapters read each user's native model, provider, and authentication configuration. They only disable unselected MCP servers per trial. A selected Hashmarks or Enola server must be registered in the host CLI configuration and proven to use the isolated trial repository. The suite does not install MCP servers or choose a model. Codex needs an explicit `model` in its host `config.toml` to make the run comparable. Native OpenCode needs a configured model. Both CLIs must have working authentication before the run.

Hashmarks on `PATH` must be the executable in the local Hashmarks `.venv`; its source commit/tree and working-copy fingerprint are recorded. Enola and both agents record their observed executable versions. A stale Hashmarks MCP registration, missing Codex MCP registration, or a server pointing outside the trial workspace yields `INCOMPLETE`, not a score. Setup examples are in Hashmarks `benchmarks/agent_evaluation/README.md`.

The source repository is pinned to commit `0841a8822f417b8fd03af61c03779df8f1cdc941` and tree `65a32888329e308615647dda194f0e36c2afe2ac`. It predates the checked-in benchmark answer JSON from the historical pilot, avoiding answer leakage. The historical v2 matrix remains available for comparison with old receipts, but v3 is the current native matrix.

Compare bare, Hashmarks, and Enola within the same agent/model configuration. The runner never computes an overall product winner. Cross-agent results are descriptive because the models, context accounting, and event surfaces differ.
