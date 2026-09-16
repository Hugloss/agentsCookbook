# Architecture

Agents Cookbook separates product concepts from runtime discovery layouts.

## Layers

### Agents

`agents/` contains actors and hard authority boundaries: who may edit, delegate, read, execute commands, or use the bounded run-artifact tools. Agents may be invoked directly when the runtime supports it.

Reviewer agents are deny-by-default. They keep normal project read-only authority and may optionally receive only `review_artifact`, a fixed-run-store sink. Primary agents may receive only `review_artifact_read` for selective named-report retrieval.

### Skills

`skills/` contains reusable methodology. Every skill is standalone and must make sense without Ping-Pong, prior reviewers, or a run store.

Skills are intentionally narrow: one hard invariant, one failure class, explicit `HUNT`, proof requirements, false-positive controls, and a preferred correction direction. The grouped catalog and overlap boundaries live in [`skills/README.md`](../skills/README.md).

### Flows

`flows/` composes agents. A flow may select, order, provide bounded context, collect results, and synthesize decisions. It must not duplicate reviewer methodology.

### Protocols

`protocols/` defines portable context/evidence conventions: bounded evidence packets, local-model context budgets, and run-artifact identity/retention rules. Protocols are not additional authority systems.

### Adapters

`adapters/` and installation/preflight scripts bridge canonical sources into OpenCode and Pi. Runtime-specific path conventions do not become repository source conventions.

Artifact storage tools are inert unless `AGENTS_COOKBOOK_RUN_DIR` is set. They accept artifact IDs rather than arbitrary paths and confine all storage to the configured per-run root.

Pi also has one runtime-authority compatibility responsibility: current `pi-open-agents` cannot derive a finite child `--tools` whitelist from canonical reviewer permissions containing `"*"`, even when the wildcard action is `deny`. The Pi adapter therefore recognizes cookbook reviewer child processes from `PI_OPEN_AGENTS_NAME`/`PI_OPEN_AGENTS_DEPTH`, sets an exact read-only active-tool set, and independently blocks any tool call outside that set. This adapter shim preserves the canonical deny-by-default agent contract rather than creating Pi-specific behavioral copies.

## Ownership

```text
agent -> authority intent
skill -> methodology
flow -> composition
protocol -> interchange/context contract
adapter -> runtime exposure + proven runtime compatibility enforcement
```

## Standalone contract

Every reviewer agent must work when:

- invoked manually;
- routed through `subagent-router` when it is one of the configured reviewers;
- composed by the full planning/build flow;
- reused by a future compatible flow.

Every skill must work when:

- loaded directly by a compatible runtime/agent;
- used by its owning reviewer when one exists;
- reused by a future compatible agent or flow.

`subagent-router` routes reviewer agents, not arbitrary skill names. Installable specialist skills therefore do not imply a matching routed reviewer or a mandatory flow step.

Artifact persistence is optional transport, never a hidden prerequisite. With artifact mode disabled, reviewers return their complete review normally. The Pi reviewer child read-only boundary remains active independently of artifact persistence.

## Low-context evidence flow

Artifact-backed mode externalizes full reports without making them disappear from authority/audit:

```text
reviewer
  -> complete skill-defined report
  -> bounded review_artifact sink
  -> compact receipt/summary returned to coordinator

coordinator
  -> synthesize from compact receipts
  -> selectively read one full report only when needed
```

The run-store checker validates exact reviewer sets, receipt identity, hashes, output sizes, summary budgets, and runtime identity. A separate post-run exporter can materialize ordinary non-artifact-mode sessions for later audit, but it does not reduce context during the original run.

## Mandatory versus installable capabilities

The repository currently installs 12 agents and 34 skills. Only eight reviewer agents are mandatory in the Ping-Pong/Ping-Ping full-review gate. Additional standalone agents and skills do not automatically enlarge that gate.

This distinction prevents new capabilities from silently changing established workflow cost or semantics.
