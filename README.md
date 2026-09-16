# Agents Cookbook

**A reusable prompt library for coding agents and repository reviewers.**

Agents Cookbook collects small, standalone Markdown prompts that can be reused in **OpenCode, Pi, or another compatible agent runtime**. The repository owns prompt methodology, role contracts, and optional composition recipes. The runtime owns execution.

## What this repository is

The core product is the Markdown prompt library:

- `skills/` contains reusable review and reasoning methodology;
- `agents/` contains thin runtime-ready prompt wrappers around skills or coordinator roles;
- `flows/` contains optional examples for composing those prompts into larger review sequences.

The prompts are designed to be copied, linked, loaded directly, manually triggered, or composed by another agent system. A skill does not need Ping-Pong state, sibling reviewers, a run store, or a particular model provider to make sense.

## What this repository is not

Agents Cookbook is **not** an agent runtime, sandbox, workflow engine, model server, repository indexer, durable state system, or orchestration framework.

OpenCode, Pi, or another host is responsible for:

- model execution and context management;
- tool execution and permissions;
- filesystem/process/network sandboxing;
- agent/session lifecycle;
- delegation mechanics;
- persistence and runtime isolation.

The adapters and scripts in this repository only make the prompt library convenient to install and validate in supported runtimes. They are not the product boundary.

## Library structure

```text
skills/       reusable prompt methodology — the library core
agents/       thin runtime-ready prompt wrappers and coordinator prompts
flows/        optional composition recipes; no unique review methodology
protocols/    portable evidence/context/output conventions
adapters/     OpenCode/Pi integration only
scripts/      installation and validation helpers
evals/        prompt-quality and discrimination cases
docs/         architecture and usage documentation
```

There is one canonical Markdown source for each skill and agent. Runtime installation links those sources into the locations each host expects rather than maintaining runtime-specific behavioral copies.

## How to reuse the library

Use the smallest layer that solves the problem:

1. **Use a skill directly** when you want one methodology, such as scouting a repository for the next worthwhile investigation, deriving defensible findings from code, stale-work race review, semantic redecision review, or test causality review.
2. **Use an agent prompt** when the host benefits from an explicit role, permission contract, model alias, or output contract around a skill.
3. **Use a flow** when you intentionally want several independent reviewer prompts composed into one planning/build sequence.

The library is standalone-first. Adding a skill does not silently add another mandatory reviewer to a flow.

## Capabilities

There are **35 installable skills**. The complete grouped catalog and overlap boundaries live in [`skills/README.md`](skills/README.md).

There are **12 installable agent prompts**:

- 3 composition prompts: `ping-pong-plan`, `ping-ping-build`, `subagent-router`;
- 8 read-only reviewer wrappers used by the optional full Ping-Pong/Ping-Ping recipe;
- 1 standalone performance reviewer wrapper: `code-performance-optimization-auditor`.

| Reviewer prompt | Methodology skill | Default local-model alias |
| --- | --- | --- |
| `plan-improver-model2` | `plan-gap-scout` | `liteLLM/gpt-oss` |
| `plan-improver-model3` | `alternative-route-challenge` | `liteLLM/gpt-oss` |
| `plan-validation-designer` | `validation-gap-finder` | `liteLLM/gpt-oss` |
| `plan-coverage-reviewer` | `coverage-design-review` | `liteLLM/gpt-oss` |
| `plan-red-team-gate` | `red-team-leftover-gate` | `liteLLM/gpt-oss` |
| `plan-implementation-simulator` | `implementation-dry-run` | `liteLLM/gpt-oss` |
| `plan-fact-auditor` | `fact-grounding-auditor` | `liteLLM/gemma4` |
| `plan-contract-checker` | `plan-contract-guard` | `liteLLM/gemma4` |

Model names are deployment aliases, not methodology requirements. Point them at any compatible endpoint while preserving the intended tool, context, and output contracts.

## Prompt design rules

Skills are intentionally small and sharp:

- one hard invariant;
- one narrow review or discovery question;
- specialist review skills own one failure class;
- explicit `HUNT` guidance;
- proof requirements before reporting;
- false-positive controls;
- preference for deletion and simplification over new layers;
- real production/test-path evidence rather than grep-only findings.

The aim is a library of prompts that stay useful across repositories and flows, including smaller local models with constrained context.

## Optional composition recipes

`ping-pong-plan` and `ping-ping-build` demonstrate one way to compose eight independent reviewer prompts while keeping their methodologies separate. `subagent-router` demonstrates choosing only one configured reviewer when a full review is unnecessary.

These are reusable prompt recipes, not a required framework. Other systems can compose the same skills and agents differently.

## Local-model context profile

The provided runtime recipes target a **98,304-token maximum context** while keeping normal working context substantially below that ceiling.

- normal working target: about 65k tokens or less;
- workflow hard target: about 73k tokens or less;
- reserve roughly 25% for tool schemas, evidence variance, reasoning/compaction, and final output;
- descriptions target <=120 characters and must be <=160 characters.

See [`protocols/context-budget.md`](protocols/context-budget.md).

## OpenCode and Pi integration

OpenCode and Pi are supported consumers of the library. Install/update the canonical prompts and narrow adapters with:

```bash
scripts/link-opencode-local.sh
```

Repository checks:

```bash
scripts/check-canonical-sources.sh
node scripts/run-skill-benchmarks.js --validate-corpus
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
```

Runtime-specific qualification remains the responsibility of the actual host environment:

```bash
scripts/preflight-opencode-ping-pong.sh
scripts/preflight-pi-ping-pong.sh
```

See [`docs/local-runtime-qualification.md`](docs/local-runtime-qualification.md) for the supported OpenCode/Pi examples.

## Optional bounded review artifacts

The prompt library does not require a run store. Reviewers can return their complete Markdown result directly.

For supported OpenCode/Pi flows, `AGENTS_COOKBOOK_RUN_DIR` can optionally externalize full reviewer reports and return compact receipts to reduce active context. This is a runtime adapter feature, not a prerequisite for using any skill or agent prompt.

See [`protocols/run-artifacts.md`](protocols/run-artifacts.md).

## Evaluation

`evals/` exists to test prompt quality and boundary discrimination. The important question is not merely whether a prompt loads, but whether it finds its own failure class and rejects safe or neighboring cases.

The actual model execution, sandboxing, and repository materialization used for evaluation belong to OpenCode, Pi, or another runtime. The cookbook supplies the prompt and evaluation contract.

## Authority conventions

When using the provided composition prompts:

- `ping-pong-plan` owns its final plan;
- `ping-ping-build` owns implementation edits in its example flow;
- reviewer prompts remain read-only evidence providers;
- skills own methodology;
- the host runtime owns execution and isolation;
- skipped or failed work must never be reported as successful.

These are prompt contracts that a host may enforce; they do not turn Agents Cookbook into an execution platform.

## Documentation

- [Skill catalog](skills/README.md)
- [Architecture](docs/architecture.md)
- [Ping-Pong planning example](docs/ping-pong-plan-flow.md)
- [Local runtime qualification](docs/local-runtime-qualification.md)
- [Run artifacts](protocols/run-artifacts.md)
- [Non-technical walkthrough](docs/non-technical-walkthrough.md)
- [Evaluation guidance](evals/README.md)
- [Sharp skill discrimination](evals/sharp-skill-discrimination.md)
- [Browser demo](demo/index.html)
