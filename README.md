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
<global>/agents/ping-pong-plan.md
  -> <agentsCookbook>/.opencode/agents/ping-pong-plan.md

<global>/prompts/*.md
  -> <agentsCookbook>/.opencode/prompts/*.md
```

The `agents` and `prompts` directories stay as real directories so existing global OpenCode files can coexist. Existing files are preserved by default; pass `--force` only when you want non-matching destinations moved to timestamped backups before linking.

Then copy `.opencode/examples/opencode.local-symlink.example.json` to a target repo's `opencode.json`, or manually merge its `agent` block into an existing target config. The example defines only the seven prompt-backed reviewer subagents. It does not define `ping-pong-plan`; OpenCode discovers that primary agent from the global `agents/ping-pong-plan.md` symlink.

To remove the cookbook global symlinks:

```sh
scripts/unlink-opencode-local.sh
```

The unlink script removes only symlinks whose resolved targets are inside this repo's `.opencode` directory. It preserves real files, real directories, unrelated symlinks, and every `opencode.json` file.

Use `--dry-run` on either script to preview changes. This setup assumes a Unix-like environment with symlink support, such as Linux, macOS, WSL, or Git Bash with symlinks enabled.

## OpenCode Agents

The required setup has one primary agent and seven subagents:

- `ping-pong-plan` is discovered from the global Markdown file symlink at `<global>/agents/ping-pong-plan.md`.
- `plan-improver-model2`
- `plan-improver-model3`
- `plan-validation-designer`
- `plan-red-team-gate`
- `plan-implementation-simulator`
- `plan-fact-auditor`
- `plan-contract-checker`

The subagent prompt mapping in the example is:

| Subagent | Prompt |
| --- | --- |
| `plan-improver-model2` | `~/.config/opencode/prompts/plan-improver.md` |
| `plan-improver-model3` | `~/.config/opencode/prompts/plan-improver.md` |
| `plan-validation-designer` | `~/.config/opencode/prompts/plan-validation-designer.md` |
| `plan-red-team-gate` | `~/.config/opencode/prompts/plan-red-team-gate.md` |
| `plan-implementation-simulator` | `~/.config/opencode/prompts/plan-implementation-simulator.md` |
| `plan-fact-auditor` | `~/.config/opencode/prompts/plan-fact-auditor.md` |
| `plan-contract-checker` | `~/.config/opencode/prompts/plan-contract-checker.md` |

`plan-improver-model2` and `plan-improver-model3` intentionally share `plan-improver.md`; they differ by model/config wiring.

This repo's `.opencode/agents/` and `.opencode/prompts/` files are the source of truth. Do not create competing global files at the cookbook symlink destinations, because doing so breaks the cookbook update path. If global files already exist at those paths, either keep them and do not link this cookbook there, or run the link script with `--force` so the existing paths are moved to timestamped backups before the symlinks are created.

## Troubleshooting Agent Calls

`opencode debug agent ping-pong-plan` verifies that the primary agent is loaded. It does not prove that a session invoked the reviewer subagents.

If the visible answer starts with an internal draft label such as `STEP0` or omits `## Subagent Run Summary`, treat that run as incomplete. The coordinator should keep draft labels internal, call the reviewer subagents with the task tool, and return only the final `# Final Plan` answer.

OpenCode task calls to subagents must include `description`, `prompt`, and `subagent_type`. If a final answer claims subagents succeeded but the session checker reports missing task calls, treat the run as invalid and rerun after fixing the prompt or config.

To check the latest run for the current repo:

```sh
scripts/check-opencode-session.sh
```

To check a specific session:

```sh
scripts/check-opencode-session.sh <session-id>
```

The checker reports one line for each required subagent and exits non-zero if any required task call is missing. The stable output lines are easy to grep:

```sh
scripts/check-opencode-session.sh | rg '^SESSION_ID=|^SUBAGENT |^SUMMARY '
```

You can also export the session manually and search for task calls:

```sh
opencode export <session-id> | rg '"tool": "task"|subagent_type|plan-improver-model2|plan-improver-model3'
```

The final `ping-pong-plan` answer must start with `# Final Plan` and include `## Subagent Run Summary`. If a required subagent was skipped or failed, the plan should say the ping-pong run is incomplete instead of claiming the full review flow completed.

## Key Idea

The reviewer agents do not replace the lead planner. They provide focused feedback, and the lead planner returns one clear final plan.
