# Agents Cookbook

Reusable local-LLM agents, skills, and composable review flows for **OpenCode and Pi**.

The cookbook is intentionally not structured around runtime discovery directories. OpenCode and Pi are deployment targets; the repository models product concepts directly.

## Repository architecture

```text
agents/       standalone actors and authority boundaries
skills/       standalone reusable review methodologies
flows/        compositions of agents; no unique reviewer methodology
protocols/    bounded evidence, context, and run-artifact contracts
adapters/     OpenCode/Pi runtime integration
evals/        evaluation ownership and benchmark guidance
docs/         architecture and usage documentation
scripts/      installation, preflight, session auditing, artifacts, and benchmarks
```

There is one canonical source for each agent and skill. Runtime installation links those sources into the locations each harness expects.

## Capabilities

There are **12 installable agents**:

- 3 flow-facing agents: `ping-pong-plan`, `ping-ping-build`, `subagent-router`;
- 8 mandatory read-only reviewers used by the full Ping-Pong/Ping-Ping gate;
- 1 standalone performance auditor: `code-performance-optimization-auditor`.

There are **8 installable skills**. Every skill and reviewer is independently usable outside the full flows; no capability requires Ping-Pong state, sibling reviewer output, or a run store.

| Reviewer | Skill | Default local-model alias |
| --- | --- | --- |
| `plan-improver-model2` | `plan-improvement-scout` | `liteLLM/gpt-oss` |
| `plan-improver-model3` | `plan-improvement-scout` | `liteLLM/gpt-oss` |
| `plan-validation-designer` | `validation-gap-finder` | `liteLLM/gpt-oss` |
| `plan-coverage-reviewer` | `coverage-design-review` | `liteLLM/gpt-oss` |
| `plan-red-team-gate` | `red-team-leftover-gate` | `liteLLM/gpt-oss` |
| `plan-implementation-simulator` | `implementation-dry-run` | `liteLLM/gpt-oss` |
| `plan-fact-auditor` | `fact-grounding-auditor` | `liteLLM/gemma4` |
| `plan-contract-checker` | `plan-contract-guard` | `liteLLM/gemma4` |

The model names are deployment aliases, not reviewer-methodology requirements. Point them at the local endpoints you want through your LiteLLM deployment while preserving the required tool use, context window, and output contracts. The standalone performance auditor defaults to `liteLLM/devstral`; it is deliberately **not** silently added to the eight-review full-flow gate.

## Standalone first

A reviewer/skill must work when composed by a full flow, another future flow, the one-reviewer router, or directly by a user. Flows may select, sequence, provide bounded context, collect results, and synthesize decisions. They do not own reviewer-specific methodology.

## Local-model context profile

The primary local profile assumes a **98,304-token maximum context**. This is a ceiling, not a normal target.

- normal working context: about 65k tokens or less;
- workflow hard target: about 73k tokens or less;
- reserve roughly 25% for tool schemas, evidence variance, reasoning/compaction, and final output;
- descriptions target <=120 characters and must be <=160 characters.

See [`protocols/context-budget.md`](protocols/context-budget.md). Real deployment promotion also requires the model-backed checks in [`docs/local-runtime-qualification.md`](docs/local-runtime-qualification.md).

## Bounded review context

Reviewers receive a self-contained evidence packet rather than the whole conversation or previous reviewer history. See [`protocols/evidence-packet.md`](protocols/evidence-packet.md).

### Live artifact-backed mode

`scripts/link-opencode-local.sh` installs narrow artifact adapters for both runtimes. They register **no artifact tools by default**. To enable live low-context transport, start the runtime with an absolute per-run root:

```bash
export AGENTS_COOKBOOK_RUN_DIR="$PWD/.runs/$(date +%Y%m%d-%H%M%S)"
```

In this mode:

```text
reviewer
  -> full skill-defined report
  -> review_artifact (bounded run store)
  -> <=1200-char receipt summary returned to MASTER

MASTER
  -> uses receipt summary by default
  -> review_artifact_read(<one reviewer id>) only when detailed evidence is needed
```

Reviewers remain deny-by-default and receive `review_artifact` but not generic project write/edit or artifact-read authority. Primary agents receive `review_artifact_read` but cannot write review artifacts. Neither model-facing tool accepts a filesystem path; writes are confined beneath the configured run root and existing artifact IDs cannot be overwritten.

After a full eight-review artifact-backed run, validate the durable evidence:

```bash
scripts/check-run-artifacts.js --run-dir "$AGENTS_COOKBOOK_RUN_DIR"
```

For a routed or manually invoked single reviewer:

```bash
scripts/check-run-artifacts.js \
  --run-dir "$AGENTS_COOKBOOK_RUN_DIR" \
  --reviewer plan-coverage-reviewer
```

Leave the environment variable unset for normal standalone behavior where reviewers return full artifacts directly.

### Post-run fallback export

Runs made without live artifact mode can still be materialized from real runtime evidence:

```bash
scripts/export-review-artifacts.js --runtime pi --input /path/to/session.jsonl --out runs/<run-id>
scripts/export-review-artifacts.js --runtime opencode --input /path/to/opencode-export.json --out runs/<run-id>
```

The fallback exporter writes immutable Markdown reports, compact receipts, hashes, and a manifest; failed calls are represented explicitly rather than invented. See [`protocols/run-artifacts.md`](protocols/run-artifacts.md).

## OpenCode and Pi

Install/update canonical agents, skills, and adapters:

```bash
scripts/link-opencode-local.sh
```

Repository/adapter qualification:

```bash
scripts/check-canonical-sources.sh
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
```

Runtime qualification on a machine with the actual harnesses and local model endpoints:

```bash
scripts/preflight-opencode-ping-pong.sh
scripts/preflight-pi-ping-pong.sh
```

Current `pi-open-agents` cannot turn a wildcard permission block into a finite child `--tools` whitelist. The Pi adapter closes that runtime-specific gap for cookbook reviewer children with an exact active-tool set (`read`, `grep`, `find`, `ls`, plus `review_artifact` only in artifact mode) and a second `tool_call` blocking gate. Canonical reviewers keep their OpenCode-compatible `"*": deny` contract; no Pi-specific behavioral copies are introduced.

Then follow [`docs/local-runtime-qualification.md`](docs/local-runtime-qualification.md) for the real OpenCode/Pi full-review acceptance runs. In artifact-backed Pi runs, `check-pi-session.js` additionally requires each successful reviewer child to have called `review_artifact` with its own fixed artifact ID.

OpenCode details live in [`adapters/opencode/`](adapters/opencode/); Pi details live in [`adapters/pi/`](adapters/pi/).

## Authority model

- `ping-pong-plan` alone owns the canonical plan;
- `ping-ping-build` alone owns implementation edits in its flow;
- reviewers are read-only evidence providers with only a bounded optional artifact sink;
- skills provide methodology;
- runtime evidence, not prose claims, proves reviewer invocation;
- failed/skipped review or validation work must never be reported as successful.

## Design direction

The cookbook borrows useful ideas from strong skill repositories—progressive disclosure, short routing metadata, selective reference loading, and context isolation—without copying another repository's taxonomy or workflows.

Its differentiators are explicit authority, independent multi-model review, standalone capabilities, dual OpenCode/Pi operation, runtime auditing, and context economics designed for local models.

## Documentation

- [Architecture](docs/architecture.md)
- [Ping-Pong planning flow](docs/ping-pong-plan-flow.md)
- [Local runtime qualification](docs/local-runtime-qualification.md)
- [Run artifacts](protocols/run-artifacts.md)
- [Non-technical walkthrough](docs/non-technical-walkthrough.md)
- [Evaluation guidance](evals/README.md)
- [Browser demo](demo/index.html)
