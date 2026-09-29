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

The benchmark composes a transient OpenCode runtime overlay while preserving the
host's native model, provider, authentication, permissions, and existing inline
configuration. Bare trials disable repository-intelligence MCP servers. Assisted
trials take the selected subject's MCP exposure from its benchmark adapter: the exact
admitted Hashmarks or Enola executable, arguments, working directory, and isolated
state/config needed for that trial. Any same-named project/global OpenCode MCP entry is
observed but shadowed for the trial; it is not benchmark subject authority.

Native OpenCode assistance is admitted only when that benchmark-owned subject exposure
can be proven to target the isolated trial workspace and the effective OpenCode MCP
command resolves to the admitted executable identity. Hashmarks is proven from its
explicit `--workspace`; Enola is proven from its explicit trial repository/config
binding. Missing executables, changed exposure identity, or unprovable/outside-workspace
bindings produce `INCOMPLETE` before agent work.

Primary interpretation is assistance gain within the same runtime/model authority.
Cross-runtime rows are descriptive only.

## Measurement boundary

The suites measure correctness, subject availability, MCP configuration/adoption,
command/tool calls, MCP evidence bytes when observable, token usage when exposed,
duration, contamination, and oracle health.

The native agent event surfaces do not authoritatively expose repository file-read
bytes, so the suites explicitly mark that archaeology metric unavailable rather than
estimating it.
OpenCode Code Mode child calls are counted from export metadata when present. Per-child
result bytes and calls without usable metadata remain unobserved.

Do not publish an overall winner score.

## Current native suites

`native-matrix-v3/` is the current native Codex/OpenCode comparison, with one paired smoke task by default from Hashmarks. It pins a source revision without checked-in answers. `enola-cycle-reproduction-v1/` adapts the published TypeScript cycle example and reports functional success and cycle introduction separately. Both are development-only experiments in agentsCookbook; neither enters the installed Hashmarks product.
