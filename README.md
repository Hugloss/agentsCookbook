# Agents Cookbook

Reusable local-LLM agents, skills, and composable review flows for **OpenCode and Pi**.

The cookbook is intentionally not structured around runtime discovery directories. OpenCode and Pi are deployment targets; the repository models the product concepts directly.

## Repository architecture

```text
agents/       standalone actors and authority boundaries
skills/       standalone reusable review methodologies
flows/        compositions of agents; no unique reviewer methodology
protocols/    bounded evidence, context, and optional run-artifact contracts
adapters/     OpenCode/Pi runtime integration notes
evals/        evaluation ownership and benchmark guidance
docs/         architecture and usage documentation
scripts/      installation, preflight, session auditing, artifacts, and benchmarks
```

There is one canonical source for each agent and skill. Runtime installation links those sources into the locations each harness expects.

## Capabilities

There are **12 installable agents**:

- 3 flow-facing agents: `ping-pong-plan`, `ping-ping-build`, `subagent-router`.
- 8 mandatory read-only reviewers used by the full Ping-Pong/Ping-Ping gate.
- 1 standalone performance auditor: `code-performance-optimization-auditor`.

There are **8 installable skills**. Every skill and reviewer is independently usable outside the full flows; no capability requires Ping-Pong state, sibling reviewer output, or a run store.

The mandatory eight reviewers remain:

| Reviewer | Skill | Model |
| --- | --- | --- |
| `plan-improver-model2` | `plan-improvement-scout` | `liteLLM/gpt-oss` |
| `plan-improver-model3` | `plan-improvement-scout` | `liteLLM/gpt-oss` |
| `plan-validation-designer` | `validation-gap-finder` | `liteLLM/gpt-oss` |
| `plan-coverage-reviewer` | `coverage-design-review` | `liteLLM/gpt-oss` |
| `plan-red-team-gate` | `red-team-leftover-gate` | `liteLLM/gpt-oss` |
| `plan-implementation-simulator` | `implementation-dry-run` | `liteLLM/gpt-oss` |
| `plan-fact-auditor` | `fact-grounding-auditor` | `liteLLM/gemma4` |
| `plan-contract-checker` | `plan-contract-guard` | `liteLLM/gemma4` |

The performance auditor uses `code-performance-optimization-audit` and `liteLLM/devstral`; it is deliberately **not** silently added to the eight-review full-flow gate.

## Standalone first

A reviewer/skill must work in all of these cases:

1. composed by `ping-pong-plan` or `ping-ping-build`;
2. composed by another future flow;
3. routed through `subagent-router`;
4. manually invoked by a user.

Flows may select, sequence, provide bounded context, collect results, and synthesize decisions. They do not own reviewer-specific methodology.

## Local-model context profile

The primary supported local profile assumes a **98,304-token maximum context**. This is a ceiling, not a normal working target.

Design targets:

- normal working context: about 65k tokens or less;
- workflow hard target: about 73k tokens or less;
- reserve roughly 25% for tool schemas, evidence variance, reasoning/compaction, and final output;
- agent/skill descriptions target <=120 characters and must be <=160 characters in this repository.

See [`protocols/context-budget.md`](protocols/context-budget.md).

## Bounded review context

Reviewers receive a self-contained evidence packet rather than the whole conversation or all previous reviewer output. See [`protocols/evidence-packet.md`](protocols/evidence-packet.md).

For low-context runs, reviewer reports can be persisted outside active context with compact deterministic receipts. Standalone reviewers do not depend on that storage.

Reviewers remain read-only. The default persistence boundary is **after the reviewer call**, using real runtime session evidence:

```bash
node scripts/export-review-artifacts.js \
  --runtime pi \
  --input /path/to/session.jsonl \
  --out runs/<run-id>

node scripts/export-review-artifacts.js \
  --runtime opencode \
  --input /path/to/opencode-export.json \
  --out runs/<run-id>
```

The exporter writes one immutable Markdown artifact and one compact JSON receipt per real reviewer call, plus `manifest.json`. It hashes every artifact and represents failed calls explicitly instead of inventing reviews. See [`protocols/run-artifacts.md`](protocols/run-artifacts.md).

A future runtime-native artifact tool may reduce live coordinator context further, but it must preserve the same rule: no generic project write authority for reviewers.

## OpenCode and Pi

Both runtimes use the same canonical `agents/` and `skills/` sources.

Install/update local links:

```bash
scripts/link-opencode-local.sh
```

Run qualification before long workflows:

```bash
scripts/check-canonical-sources.sh
scripts/preflight-opencode-ping-pong.sh
scripts/preflight-pi-ping-pong.sh
scripts/smoke-opencode-scripts.sh
```

OpenCode integration details live in [`adapters/opencode/`](adapters/opencode/); Pi details live in [`adapters/pi/`](adapters/pi/).

## Authority model

- `ping-pong-plan` alone owns the canonical plan.
- `ping-ping-build` alone owns implementation edits in its flow.
- reviewers are read-only evidence providers;
- skills provide methodology;
- runtime session evidence, not prose claims, proves reviewer invocation;
- failed/skipped reviewer or validation work must never be reported as successful.

## Design direction

The cookbook borrows useful ideas from strong skill repositories—especially progressive disclosure, short routing metadata, selective reference loading, and context isolation—but it does not copy another repository's taxonomy or workflows.

Its differentiators are explicit agent authority, independent multi-model review, reusable standalone capabilities, dual OpenCode/Pi operation, runtime invocation auditing, and context economics designed for local models.

## Documentation

- [Architecture](docs/architecture.md)
- [Ping-Pong planning flow](docs/ping-pong-plan-flow.md)
- [Non-technical walkthrough](docs/non-technical-walkthrough.md)
- [Evaluation guidance](evals/README.md)
- [Browser demo](demo/index.html)
