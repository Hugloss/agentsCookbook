# Ping-Pong Agent Flow

The cookbook exposes one multi-model workflow to both OpenCode and Pi. The
three primary agents and eight reviewers live in `.opencode/agents/`; the seven
reviewer operating contracts live in `.agents/skills/`.

## Runtime Adapter

Agent names and delegated task bodies are runtime-neutral. Only the delegation
call changes:

```text
OpenCode: task({ description, prompt, subagent_type })
Pi:       subagent({ agent, task })
```

OpenCode enforces the reviewer allowlist through `permission.task`. Pi's
`pi-open-agents` extension enforces it through `allowedAgents` and `maxDepth`.
Each primary definition carries both fields so the same Markdown works in both
environments.

## Primary Agents

| Agent | Ownership | File access | Reviewer calls |
| --- | --- | --- | --- |
| `ping-pong-plan` | Owns and returns the canonical plan. | Read-only. | All eight, once each. |
| `ping-ping-build` | Owns implementation and applies accepted feedback. | Read/write and validation commands. | All eight, once each after initial validation. |
| `subagent-router` | Chooses one reviewer for a focused request. | Read-only. | Exactly one, or none for a full-flow handoff. |

Reviewer agents never own the canonical plan or implementation and cannot
delegate. Each loads its mapped skill, which contains both normal plan-review
and `BUILD REVIEW MODE` behavior.

## Reviewer Sequence

```text
master draft
  -> plan-improver-model2 (find missing work and leftovers)
  -> plan-improver-model3 (challenge assumptions with another route)
  -> master synthesis
  -> plan-validation-designer
  -> plan-coverage-reviewer
  -> plan-red-team-gate
  -> plan-implementation-simulator
  -> plan-fact-auditor
  -> plan-contract-checker
  -> master final output
```

The master classifies findings and makes every canonical revision. A severe
gate result must be resolved before the next gate unless it is contradicted by
verified repo facts or user scope.

## Reviewer Mapping

| Reviewer | Skill | Review lens |
| --- | --- | --- |
| `plan-improver-model2` | `plan-improvement-scout` | Concrete gaps, leftovers, ownership, and validation to add before implementation. |
| `plan-improver-model3` | `plan-improvement-scout` | Assumption challenge and a genuinely different implementation route. |
| `plan-validation-designer` | `validation-gap-finder` | Concrete checks and binary acceptance criteria. |
| `plan-coverage-reviewer` | `coverage-design-review` | Real usage paths and plausible failure detection. |
| `plan-red-team-gate` | `red-team-leftover-gate` | Blockers, ambiguity, and scope creep. |
| `plan-implementation-simulator` | `implementation-dry-run` | Sequencing, ownership, and implementation feasibility. |
| `plan-fact-auditor` | `fact-grounding-auditor` | Repo evidence and assumption labeling. |
| `plan-contract-checker` | `plan-contract-guard` | Final completeness and ownership contract. |

## Context and Output Contracts

Planning delegations separate `Inspected`, `Repo Facts`, `Assumptions`,
`Unresolved Uncertainty`, `Validation Hints`, and `Not Inspected`. Build
delegations start with `BUILD REVIEW MODE` and include changed files, a diff
summary, validation results, skipped checks, and remaining risks.

`ping-pong-plan` returns `# Final Plan` with an eight-agent run summary.
`ping-ping-build` returns `# Implementation Summary` with an eight-reviewer run
summary. Missing, failed, duplicate, or unexpected calls make the workflow
incomplete; raw reviewer transcripts and internal ledgers stay private.

## Installation and Verification

`scripts/link-opencode-local.sh` links all eleven agent files into both runtimes
and links skills into `$HOME/.agents/skills`. No prompt files or copied
`opencode.json` reviewer blocks are required.

Use:

```sh
scripts/preflight-opencode-ping-pong.sh /path/to/target-repo
scripts/preflight-pi-ping-pong.sh /path/to/target-repo
scripts/smoke-opencode-scripts.sh
```

The OpenCode session checker validates actual `task` events and their
`subagent_type` values. `scripts/check-pi-session.js` validates actual Pi
`subagent` calls, their order, their results, and each child reviewer's first
skill-loading action. The Pi preflight validates Pi, `pi-open-agents`, agent
links, shared skills, and project-local shadowing before a run; it does not
claim that a later model response actually delegated.
