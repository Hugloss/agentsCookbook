# Agents Cookbook

This repository demonstrates a multi-agent planning flow. One lead planning agent creates the final implementation plan, while specialist reviewer agents check it for missing details, validation, risk, feasibility, facts, and final-answer quality.

## Start Here

- [Browser demo](demo/index.html): open this first for a clickable stakeholder walkthrough.
- [Non-technical agent demo](.opencode/NON_TECH_AGENT_DEMO.md): use this for presenter notes, scripts, and a Markdown version of the walkthrough.
- [Technical flow reference](.opencode/PING_PONG_PLAN_FLOW.md): use this when editing or auditing the actual OpenCode planning flow.

## Run The Demo

Double-click `demo/index.html`, or open it from your browser with File > Open. The demo is self-contained and does not need a dev server, network access, installed packages, or a build step.

## Global OpenCode Setup

This setup keeps one global set of cookbook symlinks up to date. Target repos do not need cookbook `.opencode` files; they only need an `opencode.json` copied from the example or merged with its `agent` block.

From this repo, link the cookbook assets into your global OpenCode config directory:

```sh
scripts/link-opencode-local.sh
```

By default, the script uses `${XDG_CONFIG_HOME:-$HOME/.config}/opencode`, which matches the path reported by `opencode debug paths` on current OpenCode installs. For tests or custom installs, pass `--global-dir /path/to/opencode-config`; if that path is not `~/.config/opencode`, adjust the copied example's prompt paths to match.

The script creates absolute symlink entries:

```text
<global>/agents/*.md
  -> <agentsCookbook>/.opencode/agents/*.md

<global>/prompts/*.md
  -> <agentsCookbook>/.opencode/prompts/*.md

<global>/skills/*/
  -> <agentsCookbook>/.opencode/skills/*/
```

The `agents`, `prompts`, and `skills` directories stay as real directories so existing global OpenCode files can coexist. Existing files are preserved by default; pass `--force` only when you want non-matching destinations moved to timestamped backups before linking.

Then copy `.opencode/examples/opencode.local-symlink.example.json` to a target repo's `opencode.json`, or manually merge its `agent` block into an existing target config. The example defines only the seven prompt-backed reviewer subagents. It does not define primary agents; OpenCode discovers `ping-pong-plan`, `ping-ping-build`, and `subagent-router` from the global `agents/*.md` symlinks.

To remove the cookbook global symlinks:

```sh
scripts/unlink-opencode-local.sh
```

The unlink script removes only symlinks whose resolved targets are inside this repo's `.opencode` directory. It preserves real files, real directories, unrelated symlinks, and every `opencode.json` file.

Use `--dry-run` on either script to preview changes. This setup assumes a Unix-like environment with symlink support, such as Linux, macOS, WSL, or Git Bash with symlinks enabled.

## Before Long Runs

Before starting a long `ping-pong-plan` or `ping-ping-build` run from a target repo, verify the effective setup:

```sh
scripts/link-opencode-local.sh --dry-run
scripts/preflight-opencode-ping-pong.sh /path/to/target-repo
```

The preflight script is read-only. It checks that the global cookbook symlinks point at this checkout, the target repo has the seven reviewer subagents configured with global prompt paths and scoped specialty-skill access, the primary agent prompts contain their strict task rules, and reviewers are effectively read-only in OpenCode. It also fails early if other OpenCode processes are running, because concurrent sessions can cause OpenCode database checkpoint errors during debug checks. If you only want filesystem and `opencode.json` checks, use `--quick`; if you intentionally want to run full preflight anyway, set `OPENCODE_PREFLIGHT_ALLOW_RUNNING=1`.

For custom config locations, keep the expected prompt base explicit:

```sh
scripts/preflight-opencode-ping-pong.sh --global-dir /path/to/opencode --prompt-base /path/to/opencode/prompts --quick /path/to/target-repo
```

If the preflight fails after you changed links, prompts, or skills, run `scripts/link-opencode-local.sh`, restart OpenCode, and run the preflight again. If OpenCode reports a `PRAGMA wal_checkpoint` failure during preflight, close other running OpenCode sessions and rerun the check before starting the long session.

## OpenCode Agents

The required setup has three primary agents and seven reviewer subagents:

The primary agents are:

- `ping-pong-plan` is planning-only and is discovered from the global Markdown file symlink at `<global>/agents/ping-pong-plan.md`.
- `ping-ping-build` is implementation mode and is discovered from the global Markdown file symlink at `<global>/agents/ping-ping-build.md`.
- `subagent-router` is a one-off read-only dispatcher discovered from the global Markdown file symlink at `<global>/agents/subagent-router.md`.

Use `ping-pong-plan` when you want a plan or review without code changes. In that mode, words like "fix", "change", "update", "refactor", and "implement" mean "produce a written plan for that future work"; they do not mean edit files. Use `ping-ping-build` only when you want OpenCode to edit files. In build mode, `ping-ping-build` is the only agent allowed to change files; the seven reviewer subagents stay read-only and only provide feedback.

Use `subagent-router` when you want feedback from one reviewer without writing the task payload yourself. If you name a reviewer, the router uses that exact `subagent_type`; otherwise it chooses the best-fit reviewer from your request. It calls exactly one reviewer and returns `# Subagent Router Result`; it is not a replacement for the full seven-reviewer `ping-pong-plan` or `ping-ping-build` flows.

Example `subagent-router` requests:

```text
Ask plan-fact-auditor to check this plan for unsupported repo claims: <plan>
Find missing tests and acceptance criteria in this plan: <plan>
Review this plan for blockers and scope creep: <plan>
Give me one reviewer opinion on this implementation plan: <plan>
```

The reviewer subagents are:

- `plan-improver-model2`
- `plan-improver-model3`
- `plan-validation-designer`
- `plan-red-team-gate`
- `plan-implementation-simulator`
- `plan-fact-auditor`
- `plan-contract-checker`

The subagent prompt and specialty-skill mapping in the example is:

| Subagent | Prompt | Skill |
| --- | --- | --- |
| `plan-improver-model2` | `~/.config/opencode/prompts/plan-improver.md` | `plan-improvement-scout` |
| `plan-improver-model3` | `~/.config/opencode/prompts/plan-improver.md` | `plan-improvement-scout` |
| `plan-validation-designer` | `~/.config/opencode/prompts/plan-validation-designer.md` | `validation-gap-finder` |
| `plan-red-team-gate` | `~/.config/opencode/prompts/plan-red-team-gate.md` | `red-team-leftover-gate` |
| `plan-implementation-simulator` | `~/.config/opencode/prompts/plan-implementation-simulator.md` | `implementation-dry-run` |
| `plan-fact-auditor` | `~/.config/opencode/prompts/plan-fact-auditor.md` | `fact-grounding-auditor` |
| `plan-contract-checker` | `~/.config/opencode/prompts/plan-contract-checker.md` | `plan-contract-guard` |

`plan-improver-model2` and `plan-improver-model3` intentionally share `plan-improver.md`; they differ by model/config wiring.

The specialty skills live in `.opencode/skills/`. They are concise checklists that help the existing agents find new improvement ideas, missing gaps, leftovers, validation holes, factual issues, and contract problems. Skills do not replace the prompts or the required reviewer task calls.

This repo's `.opencode/agents/`, `.opencode/prompts/`, and `.opencode/skills/` files are the source of truth. Do not create competing global files at the cookbook symlink destinations, because doing so breaks the cookbook update path. If global files already exist at those paths, either keep them and do not link this cookbook there, or run the link script with `--force` so the existing paths are moved to timestamped backups before the symlinks are created.

## Troubleshooting Agent Calls

`opencode debug agent ping-pong-plan`, `opencode debug agent ping-ping-build`, or `opencode debug agent subagent-router` verifies that a primary agent is loaded. It does not prove that a session invoked the reviewer subagents.

`ping-pong-plan` must never edit files. If a request says "fix this file", "implement this", or otherwise asks for file changes, `ping-pong-plan` should still return only a written `# Final Plan`. Use `ping-ping-build` in a fresh session for actual changes. Do not solve this by granting write access to `ping-pong-plan`.

If the visible answer starts with an internal draft label such as `STEP0` or omits `## Subagent Run Summary`, treat that run as incomplete. The coordinator should keep draft labels internal, call the reviewer subagents with the task tool, and return only the final `# Final Plan` answer.

OpenCode task calls to subagents must include `description`, `prompt`, and `subagent_type`. If a final answer claims subagents succeeded but the session checker reports missing task calls, treat the run as invalid and rerun after fixing the prompt or config.

For `subagent-router`, the same checker validates exactly one routed reviewer call in the selected scope. Use `--expect-subagent` when you asked for a specific reviewer:

```sh
scripts/check-opencode-session.sh --expect-subagent plan-fact-auditor <session-id>
scripts/check-opencode-session.sh --expect-subagent plan-validation-designer <session-id>
```

Use `--expect-no-subagent` when the router request is supposed to explain that no reviewer call should happen:

```sh
scripts/check-opencode-session.sh --scope session --expect-no-subagent <session-id>
```

To check the latest run for the current repo:

```sh
scripts/check-opencode-session.sh
```

To check a specific session:

```sh
scripts/check-opencode-session.sh <session-id>
```

For compact or machine-readable output:

```sh
scripts/check-opencode-session.sh --failures-only <session-id>
scripts/check-opencode-session.sh --json <session-id>
```

By default, the checker validates the latest primary-agent segment, not the entire session history. This matters when a session was resumed with a different agent: old reviewer calls from an earlier prompt must not count as proof that the latest `ping-pong-plan`, `ping-ping-build`, or `subagent-router` turn delegated correctly.

Use the scope options when you need a different view:

```sh
scripts/check-opencode-session.sh --scope latest-segment <session-id>
scripts/check-opencode-session.sh --scope latest-turn <session-id>
scripts/check-opencode-session.sh --scope session <session-id>
```

`latest-segment` is the default and checks from the latest `ping-pong-plan`, `ping-ping-build`, or `subagent-router` switch. `latest-turn` checks only after the latest user prompt. `session` is useful for historical audit context, but it can hide later missed delegation because earlier reviewer calls are counted.

For `ping-pong-plan` and `ping-ping-build`, the checker reports one line for each required subagent in the selected scope and exits non-zero if any required task call is missing, duplicated, if the scope used an unexpected task target such as `general` or a missing `subagent_type`, or if the same session mixed `ping-pong-plan` and `ping-ping-build`. For `subagent-router`, it reports `ROUTER_SUBAGENT`, `ROUTER_EXPECTED`, and `ROUTER_SUMMARY`, and exits non-zero unless exactly one allowed reviewer was called, or zero reviewer calls were explicitly requested with `--expect-no-subagent`.

```sh
scripts/check-opencode-session.sh | rg '^SESSION_ID=|^TIMELINE_SOURCE=|^CHECK_SCOPE=|^SCOPE_|^AGENT_LOG=|^SESSION_CREATED_AGENT=|^SESSION_PRIMARY_AGENTS=|^PRIMARY_AGENT |^MIXED_PRIMARY_AGENT |^ROUTER_|^SUBAGENT |^DUPLICATE_SUBAGENT |^UNEXPECTED_TASK |^INVALID_TOOL |^FORBIDDEN_PLANNING_TOOL_ATTEMPT |^SUMMARY '
```

By default, the checker reads `${XDG_DATA_HOME:-$HOME/.local/share}/opencode/opencode.db` to build an accurate message, agent-switch, and task-call timeline. Use `--db PATH` for a custom database. If the database is unavailable, the checker falls back to `opencode export`; scoped validation then requires `--scope session` because export text does not reliably expose turn boundaries.

The checker also scans `${XDG_DATA_HOME:-$HOME/.local/share}/opencode/log` for extra primary-agent evidence. Use `--log-dir DIR` for a custom log location, or `--no-agent-log-check` when you only want DB/export validation. `AGENT_LOG=missing` means no matching log evidence was found, so the checker relies on the DB/export source.

If `MIXED_PRIMARY_AGENT status=fail`, start a fresh session with only one primary workflow agent. Resuming a `ping-ping-build` session with `ping-pong-plan`, or the reverse, makes the session evidence ambiguous and should not be used as proof that the full review flow ran.

If the checker prints `INVALID_TOOL tool=write`, `INVALID_TOOL tool=edit`, or `INVALID_TOOL tool=bash` for a `ping-pong-plan` scope, or the stable `FORBIDDEN_PLANNING_TOOL_ATTEMPT` line, treat the run as invalid. That means the planning agent tried to implement with a tool it is not allowed to use. Rerun `scripts/link-opencode-local.sh`, restart OpenCode so the strict prompt reloads, and start a fresh `ping-ping-build` session if actual file changes are wanted.

Any `UNEXPECTED_TASK` line means the run should be treated as invalid; rerun `scripts/link-opencode-local.sh`, restart OpenCode, and run the request again.

You can also export the session manually and search for task calls:

```sh
opencode export <session-id> | rg '"tool": "task"|subagent_type|plan-improver-model2|plan-improver-model3'
```

The final `ping-pong-plan` answer must start with `# Final Plan` and include `## Subagent Run Summary`. The final `ping-ping-build` answer must start with `# Implementation Summary` and include `## Reviewer Run Summary`. If a required reviewer was skipped or failed, the answer should say the review loop is incomplete instead of claiming the full review flow completed.

## Benchmark Loop

Use `scripts/run-opencode-benchmarks.js` to replay the fixed local benchmark set in a temporary HOME and write per-benchmark artifacts under a run directory. It validates the resulting sessions with `scripts/check-opencode-session.sh` and keeps the Markdown scorecards in `.opencode/evals/` as the manual review rubric.

```sh
scripts/run-opencode-benchmarks.js --list
scripts/run-opencode-benchmarks.js --suite ping-pong-plan
scripts/run-opencode-benchmarks.js --suite subagent-router --benchmark full-flow-requested
scripts/run-opencode-benchmarks.js --artifacts-dir /tmp/agents-cookbook-benchmarks
```

Use `--suite` and `--benchmark` to narrow the replay set. The `subagent-router` benchmark set includes a no-reviewer handoff case, so the runner pairs that benchmark with `scripts/check-opencode-session.sh --expect-no-subagent`.

## Script Smoke Tests

The shell smoke test uses only temporary directories. It verifies link/unlink idempotency, force backups, quick preflight behavior, preservation of unrelated paths, and that link does not create a target `opencode.json`:

```sh
scripts/smoke-opencode-scripts.sh
```

## Key Idea

The reviewer agents do not replace the lead planner. They provide focused feedback, and the lead planner returns one clear final plan.
