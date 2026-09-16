# Ping-Pong Plan Flow

The same canonical agent definitions run in OpenCode and Pi. Runtime adapters expose them through each harness's discovery and delegation conventions.

## Sources

```text
agents/    authority and actor definitions
skills/    standalone review methodologies
flows/     compositions
protocols/ bounded context and optional external-memory contracts
```

OpenCode and Pi runtime locations are installation targets, not repository sources.

## Delegation adapter

```text
OpenCode: task({ description, prompt, subagent_type })
Pi:       subagent({ agent, task })
```

OpenCode constrains reviewers with `permission.task`. Pi + `pi-open-agents` uses `allowedAgents` and `maxDepth`. The same canonical Markdown carries both compatible fields.

## Full planning sequence

```text
MASTER v1
  -> gap completion
  -> alternative route
  -> MASTER synthesis
  -> validation design
  -> coverage design
  -> red team
  -> implementation simulation
  -> fact audit
  -> contract check
  -> FINAL MASTER
```

The exact eight mandatory reviewers are listed in the root README. The standalone performance auditor is installable and manually/compositionally reusable but is not part of this mandatory gate.

## Context discipline

Each reviewer receives a bounded, self-contained evidence packet. Later reviewers do not receive raw sibling reports by default. Material findings are synthesized into the current plan; optional external run artifacts can retain full detail outside active context.

The supported local profile assumes a 98,304-token maximum context, with normal work targeted substantially below that ceiling.

## Truth and completion

A reviewer counts only when the runtime records a real call to the exact reviewer and returns usable output. Missing, failed, duplicate, skipped, or unexpected mandatory calls make the flow incomplete. Session checkers validate runtime evidence instead of trusting final-answer prose.
