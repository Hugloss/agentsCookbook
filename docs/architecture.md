# Architecture

Agents Cookbook separates product concepts from runtime discovery layouts.

## Layers

### Agents

`agents/` contains actors and hard authority boundaries: who may edit, delegate, read, or execute commands. Agents may be invoked directly when the runtime supports it.

### Skills

`skills/` contains reusable methodology. Every skill is standalone and must make sense without Ping-Pong, prior reviewers, or a run store.

### Flows

`flows/` composes agents. A flow may select, order, provide bounded context, collect results, and synthesize decisions. It must not duplicate reviewer methodology.

### Protocols

`protocols/` defines portable context/evidence conventions. Protocols are not additional authority systems.

### Adapters

`adapters/` and installation/preflight scripts bridge canonical sources into OpenCode and Pi. Runtime-specific path conventions do not become repository source conventions.

## Ownership

```text
agent -> authority
skill -> methodology
flow -> composition
protocol -> interchange/context contract
adapter -> runtime exposure
```

## Standalone contract

Every reviewer and skill must work when:

- invoked manually;
- routed through the one-reviewer router;
- composed by the full planning/build flow;
- reused by a future flow.

Optional infrastructure such as run-local artifact persistence must not become a hidden prerequisite.

## Mandatory versus installable capabilities

The repository currently installs 12 agents and 8 skills. Only eight reviewer agents are mandatory in the Ping-Pong/Ping-Ping full-review gate. Additional standalone agents do not automatically enlarge that gate.

This distinction prevents new capabilities from silently changing established workflow cost or semantics.
