# Repository Intelligence Agent Matrix v2

This experiment extends pilot-v1 without modifying it.

It freezes the same three task families against a newer exact agentsCookbook source:
- commit: `6ce8b0d9230dd9bc5369ddf495ad9404766fbbaf`
- tree: `1e253d251f8e0a874aeca0b05358b36253a714cc`

The matrix is 3 subjects × 2 agent/model conditions:
- bare, Hashmarks, Enola
- Codex runtime + `gpt-5.6-sol` with high reasoning effort
- the same Codex runtime + Ollama `gemma4:12b`

Using the same Codex execution runtime keeps shell, workspace-edit, MCP wiring, JSONL
event collection, budgets and contamination semantics constant. The local condition
changes the model/provider rather than introducing a second coding-agent harness.

Primary interpretation is paired assistance within one agent/model:
`bare -> Hashmarks` and `bare -> Enola`.

Cross-model rows are descriptive. Do not convert them into an overall winner score;
hardware, inference implementation and model size remain material confounders.

The local condition is admitted only when `ollama` is available and
`ollama show gemma4:12b` succeeds. The observed Ollama executable and model descriptor
are bound into execution authority. Missing local infrastructure is INCOMPLETE, not FAIL.

Gemma v2 requires no OpenAI credential. The Sol conditions still use isolated
`CODEX_HOME` and may receive credential-only auth via `--codex-auth`.

Validate:

```bash
python -m benchmarks validate-suite \
  --suite benchmarks/suites/repository-intelligence/agent-matrix-v2
python -m benchmarks plan \
  --suite benchmarks/suites/repository-intelligence/agent-matrix-v2
```

A complete sweep contains 18 frozen definitions.
