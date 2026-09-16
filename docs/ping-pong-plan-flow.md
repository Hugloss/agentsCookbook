# Ping-Pong Plan Flow

The same canonical agent definitions run in OpenCode and Pi. Runtime adapters expose them through each harness's discovery and delegation conventions.

## Sources

```text
agents/    authority and actor definitions
skills/    standalone review methodologies
flows/     compositions
protocols/ bounded context and run-artifact contracts
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

The exact eight mandatory reviewers are listed in the root README. The standalone performance auditor is installable and reusable but is not part of this mandatory gate.

## Context discipline

Each reviewer receives a bounded, self-contained evidence packet. Later reviewers do not receive raw sibling reports by default. The supported local profile assumes a 98,304-token maximum context with normal work targeted substantially below that ceiling.

When `AGENTS_COOKBOOK_RUN_DIR` is unset, reviewers return their complete skill-defined artifacts normally.

When live artifact-backed mode is enabled:

```text
reviewer full report
  -> review_artifact
  -> immutable run-local Markdown + JSON receipt
  -> <=1200-char material-finding summary returned to MASTER
```

MASTER works from that compact receipt by default. `review_artifact_read` is reserved for one named report when a material finding is ambiguous, conflicts with verified facts/another finding, or a severe result cannot be resolved safely from the summary. The flow must not bulk-read all reports merely because they exist.

This is different from the post-run exporter: post-run export improves audit/reuse after an ordinary run, while live artifact-backed mode reduces active coordinator context during the run.

## Truth and completion

A reviewer counts only when the runtime records a real call to the exact reviewer and returns usable output or a valid compact artifact receipt. Missing, failed, duplicate, skipped, or unexpected mandatory calls make the flow incomplete.

In Pi artifact-backed mode, `check-pi-session.js` additionally requires evidence that each successful reviewer loaded its exact skill first and called `review_artifact` with its own fixed artifact ID. `check-run-artifacts.js` validates the resulting exact-eight run store, hashes, receipt identities, and summary budgets.

OpenCode full preflight validates effective reviewer/primary tool permissions. Durable run artifacts provide a second independent proof that the bounded artifact writes completed.
