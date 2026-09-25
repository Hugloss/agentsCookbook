# Repository Intelligence Agent Matrix v2

This experiment extends pilot-v1 without modifying it.

It freezes the same three task families against newer exact agentsCookbook source:

- commit: `6ce8b0d9230dd9bc5369ddf495ad9404766fbbaf`
- tree: `1e253d251f8e0a874aeca0b05358b36253a714cc`

The matrix is three repository-intelligence conditions by two explicit
model/provider conditions:

- bare, Hashmarks, Enola;
- Codex runtime + `gpt-5.6-sol` + high reasoning effort;
- the same Codex runtime + Ollama `gemma4:12b`.

That produces exactly 18 frozen definitions.

## Interpretation

Using the same Codex execution runtime keeps shell, workspace editing, MCP wiring,
JSONL event collection, budgets, contamination semantics, and receipt handling
constant. The local condition changes model/provider rather than introducing a second
coding-agent harness.

The primary comparison is paired assistance within one model/runtime:

- bare -> Hashmarks;
- bare -> Enola.

Cross-model rows are descriptive only. They answer questions such as whether
repository intelligence changes the behavior of a local model differently from the
hosted Sol model. They are not a winner ranking: hardware, inference backend, model
architecture, and model size remain confounders.

The shared seed is a benchmark identity/pairing input. It does not claim that either
model's sampler is seedable.

## Local-model authority

The Gemma condition is admitted only when:

- `codex` is available;
- `ollama` is available;
- `ollama show gemma4:12b` succeeds.

The receipt binds the observed Codex and Ollama executable identities plus a SHA-256
of the installed model descriptor. If the `gemma4:12b` tag points to different local
bytes/configuration later, it produces a different execution identity. A results
directory containing two executions of one frozen definition is rejected by reporting
instead of silently combining them.

Remote Codex credentials are explicitly blanked for the local-provider condition.
Missing Ollama, missing Gemma, provider startup failures, and model/provider transport
failures remain `INCOMPLETE`, not task `FAIL`.

## Hosted-model authority

The Sol condition freezes:

- model: `gpt-5.6-sol`;
- reasoning effort: `high`;
- provider: hosted/default Codex provider path.

Its Codex state lives under an isolated `CODEX_HOME`. Authentication can be supplied
with a credential-only `auth.json` seed or with an already exported supported
credential environment variable. Credential contents are never written to benchmark
receipts.

## Validate

```bash
python -m benchmarks validate-suite \
  --suite benchmarks/suites/repository-intelligence/agent-matrix-v2

python -m benchmarks plan \
  --suite benchmarks/suites/repository-intelligence/agent-matrix-v2
```

The plan must contain exactly 18 unique definition identities.

## Run

Keep campaign output outside the repository:

```bash
root="${TMPDIR:-/tmp}/agents-cookbook-ri-agent-matrix-v2"

python -m benchmarks run \
  --suite benchmarks/suites/repository-intelligence/agent-matrix-v2 \
  --source . \
  --cache "$root/cache" \
  --work "$root/work" \
  --results "$root/results" \
  --codex-auth "$HOME/.codex/auth.json"
```

The same command runs both model/provider conditions. The auth seed is used only for
hosted Codex conditions; local Ollama conditions explicitly disable remote Codex
credentials.

A local-only diagnostic can be narrowed without changing the frozen experiment:

```bash
python -m benchmarks run \
  --suite benchmarks/suites/repository-intelligence/agent-matrix-v2 \
  --source . \
  --cache "$root/cache" \
  --work "$root/work" \
  --results "$root/results" \
  --condition hashmarks-gemma4-12b
```

## Report

```bash
python -m benchmarks report \
  --suite benchmarks/suites/repository-intelligence/agent-matrix-v2 \
  --results "$root/results"
```

The report contains:

- per-condition outcome/economics profiles;
- per-agent/model profiles;
- paired bare -> Hashmarks/Enola assistance rows within one model;
- descriptive side-by-side cross-agent observations.

It does not calculate an overall winner.

## Measurement boundary

Codex JSONL exposes commands, MCP calls/results, file changes, token usage, and
duration. It does not authoritatively expose repository file-read bytes, so v2 does
not manufacture or enforce an archaeology-byte metric.
