# Repository Intelligence Agent Matrix v2

This experiment extends pilot-v1 without modifying it.

It freezes the same three task families against exact agentsCookbook source:

- commit: `6ce8b0d9230dd9bc5369ddf495ad9404766fbbaf`
- tree: `1e253d251f8e0a874aeca0b05358b36253a714cc`

The matrix is three repository-intelligence conditions by two agent runtimes:

- bare, Hashmarks, Enola;
- Codex with frozen `gpt-5.6-sol` + high reasoning effort;
- **native OpenCode**, using the model/provider/auth already configured on the host.

That produces exactly 18 frozen definitions.

## Hard boundary: Gemma never runs through Codex

The benchmark has no Codex local-provider/Gemma condition. Codex is used for Codex.
Local models such as Gemma are exercised through the user's already-working OpenCode
installation.

The OpenCode agent definition intentionally contains no model, provider, base URL, or
credential configuration. Those remain native OpenCode authority.

If native OpenCode currently resolves to Gemma, the run records that observed
provider/model. If native OpenCode later resolves to another model/config, that changes
execution identity instead of silently reusing the earlier result.

## Native OpenCode behavior

OpenCode inherits the user's real HOME/XDG configuration and credentials. The
benchmark does **not** copy or recreate its provider/model configuration.

Before admission the adapter runs native `opencode --pure debug config` and records:

- OpenCode executable/version identity;
- the resolved build-agent/default model;
- provider inferred from that model;
- a SHA-256 of the effective configuration after recursively redacting credential-like
  values;
- the names of configured native MCP servers.

For comparison control, the benchmark adds only an in-memory
`OPENCODE_CONFIG_CONTENT` tool overlay. It never contains model/provider/auth fields.
It disables all discovered native MCP tool prefixes except the subject selected by the
condition:

- bare: all discovered MCP tools disabled;
- Hashmarks: only `hashmarks_*` enabled;
- Enola: only `enola_*` enabled.

The selected Hashmarks/Enola MCP server must already exist and be enabled in native
OpenCode configuration. The benchmark does not duplicate its command/configuration.

`--pure` disables external OpenCode plugins during the measurement while retaining
native provider/model/auth configuration.

## Interpretation

Primary comparisons remain assistance gain inside one runtime/model authority:

- Codex bare -> Codex + Hashmarks / Enola;
- native OpenCode bare -> native OpenCode + Hashmarks / Enola.

Cross-runtime rows are descriptive only. They do not produce a winner ranking.

The shared seed is experiment identity/pairing evidence; it is not a claim that either
model sampler is seedable.

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

The Codex auth seed is used only by Codex conditions. OpenCode conditions use the
already-working native OpenCode configuration/authentication.

A native OpenCode diagnostic can be narrowed without changing the frozen experiment:

```bash
python -m benchmarks run \
  --suite benchmarks/suites/repository-intelligence/agent-matrix-v2 \
  --source . \
  --cache "$root/cache" \
  --work "$root/work" \
  --results "$root/results" \
  --condition hashmarks-opencode-native
```

## Report

```bash
python -m benchmarks report \
  --suite benchmarks/suites/repository-intelligence/agent-matrix-v2 \
  --results "$root/results"
```

The report contains per-condition profiles, per-agent profiles, paired assistance rows,
and descriptive cross-agent observations. It never calculates an overall winner.

## Measurement boundary

Codex JSONL and OpenCode session export expose different native event shapes. Both are
projected only into the generic experiment metrics needed for comparison: task outcome,
tool/MCP adoption, token counts when available, output evidence, duration, and
contamination.

Neither surface authoritatively exposes repository file-read bytes, so v2 does not
manufacture an archaeology-byte metric.
