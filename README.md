# Agents Cookbook

This repository provides the same eleven-agent planning and implementation
workflows in OpenCode and in Pi with `pi-open-agents`.

## Start Here

- [Browser demo](demo/index.html)
- [Non-technical walkthrough](.opencode/NON_TECH_AGENT_DEMO.md)
- [Technical flow reference](.opencode/PING_PONG_PLAN_FLOW.md)

## Architecture

There is one source of truth for each reusable component:

```text
.opencode/agents/*.md      3 primary agents + 8 reviewer agents
.agents/skills/*/SKILL.md  7 reviewer operating contracts
opencode.json              schema-only project config
```

Reviewer prompts are intentionally not stored separately. Each reviewer is a
real Markdown agent that loads one dedicated skill. OpenCode discovers the
agents directly; Pi discovers those same files through `pi-open-agents`.

The primary agents are:

- `ping-pong-plan`: read-only eight-reviewer planning workflow.
- `ping-ping-build`: implements changes, validates, then runs eight read-only reviews.
- `subagent-router`: sends one request to the best matching reviewer.

The reviewer mapping is:

| Reviewer | Model | Dedicated skill |
| --- | --- | --- |
| `plan-improver-model2` | `liteLLM/gpt-oss` | `plan-improvement-scout` (gap completion) |
| `plan-improver-model3` | `liteLLM/gpt-oss` | `plan-improvement-scout` (alternative route) |
| `plan-validation-designer` | `liteLLM/gpt-oss` | `validation-gap-finder` |
| `plan-coverage-reviewer` | `liteLLM/gpt-oss` | `coverage-design-review` |
| `plan-red-team-gate` | `liteLLM/gpt-oss` | `red-team-leftover-gate` |
| `plan-implementation-simulator` | `liteLLM/gpt-oss` | `implementation-dry-run` |
| `plan-fact-auditor` | `liteLLM/gemma4` | `fact-grounding-auditor` |
| `plan-contract-checker` | `liteLLM/gemma4` | `plan-contract-guard` |

## Install for OpenCode and Pi

Requirements:

- OpenCode with access to the configured `liteLLM/*` models.
- Pi 0.85.0 or newer.
- `pi-open-agents` 0.1.20 installed and enabled in Pi:

```sh
pi install npm:pi-open-agents@0.1.20
```

Install the cookbook links globally:

```sh
scripts/link-opencode-local.sh
```

The defaults are:

```text
${XDG_CONFIG_HOME:-$HOME/.config}/opencode/agents/*.md
  -> <checkout>/.opencode/agents/*.md

${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/agents/*.md
  -> <checkout>/.opencode/agents/*.md

$HOME/.agents/skills/*
  -> <checkout>/.agents/skills/*
```

Use `--global-dir`, `--pi-agent-dir`, or `--shared-skill-dir` for custom
locations. Use `--dry-run` to preview changes and `--force` to back up a
conflicting destination before linking. The installer also removes only
cookbook-owned broken symlinks from the retired global `prompts` and OpenCode
`skills` layout. It does not edit runtime settings or project configs.

Target repositories need no copied reviewer config. A target's existing
`opencode.json` may remain in place; avoid defining the same agent names there
or in project-local agent directories because those definitions can shadow the
global cookbook agents.

To remove cookbook-owned links:

```sh
scripts/unlink-opencode-local.sh
```

## Runtime Delegation

The primary-agent instructions adapt to the tool that the runtime exposes:

```text
OpenCode: task({ description, prompt, subagent_type })
Pi:       subagent({ agent, task })
```

The reviewer names remain identical in both environments. Never translate a
reviewer name into a generic agent type and never use Pi's argument shape in an
OpenCode `task` call.

## Preflight and Validation

Run both read-only preflights before a long workflow:

```sh
scripts/preflight-opencode-ping-pong.sh /path/to/target-repo
scripts/preflight-pi-ping-pong.sh /path/to/target-repo
```

OpenCode's `--quick` mode checks files, links, mappings, and source contracts
without running `opencode debug`. Both preflights accept the corresponding
custom directory flags used by the linker.

To audit an OpenCode session's actual reviewer calls:

```sh
scripts/check-opencode-session.sh <session-id>
scripts/check-opencode-session.sh --expect-subagent plan-fact-auditor <session-id>
```

To audit a Pi JSONL session's actual reviewer calls and verify that every
reviewer loaded its mapped skill first:

```sh
scripts/check-pi-session.js /path/to/session.jsonl
scripts/check-pi-session.js --scope session <session-id>
```

With no argument, the Pi checker selects the latest session for the current
directory. The OpenCode checker derives results from `task` calls with
`subagent_type`; the Pi checker derives them from `subagent` calls with `agent`
and the child tool trace. Neither trusts success claims in final-answer prose.

Preflight proves that a runtime is configured and capable of delegation. Only
a session checker proves that delegation actually happened during a run.

Run repository smoke tests with:

```sh
scripts/smoke-opencode-scripts.sh
```

The smoke test uses temporary directories and covers both runtime link trees,
legacy-link migration, preflights, OpenCode session-schema checking, Pi
invocation and skill-load traces, dishonest summaries, failed-review
continuation, idempotency, conflict backups, and safe unlinking.

## Troubleshooting `Unknown agent type`

Run the linker and both preflights, then start a fresh runtime session. In
OpenCode, confirm a reviewer directly with:

```sh
opencode debug agent plan-improver-model2
```

If that succeeds but an old session still reports `Unknown agent type`, the old
session loaded stale config or used Pi's `{agent, task}` call shape. New
OpenCode sessions must use `subagent_type`; Pi sessions must have
`pi-open-agents` enabled and use `agent`.

## Benchmarks

The manual scorecards are in `.opencode/evals/`. The OpenCode replay wrapper is:

```sh
scripts/run-opencode-benchmarks.js --list
scripts/run-opencode-benchmarks.js --suite ping-pong-plan
```
