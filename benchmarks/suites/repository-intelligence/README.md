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

The benchmark composes only a transient enable/disable and tool-gating overlay with
native OpenCode configuration, including any host `OPENCODE_CONFIG_CONTENT` layer.
The bare trial disables native MCP servers; an assisted trial reuses the host's
already-configured native `hashmarks` or `enola` server and disables the others.
agentsCookbook does not mirror the selected server command/configuration. Model,
provider, authentication, and subject MCP configuration stay with OpenCode.

Native OpenCode assistance is admitted only when the selected server can be proven to
target the isolated trial workspace. Hashmarks is proven from its resolved
`--workspace`; Enola's normal no-argument registration is proven from OpenCode's MCP
working-directory semantics. Unprovable or outside-workspace bindings remain native
and unchanged, but the trial is recorded as `INCOMPLETE`.

Primary interpretation is assistance gain within the same runtime/model authority.
Cross-runtime rows are descriptive only.

## Measurement boundary

The suites measure correctness, subject availability, MCP configuration/adoption,
command/tool calls, MCP evidence bytes when observable, token usage when exposed,
duration, contamination, and oracle health.

The native agent event surfaces do not authoritatively expose repository file-read
bytes, so the suites explicitly mark that archaeology metric unavailable rather than
estimating it.

Do not publish an overall winner score.
