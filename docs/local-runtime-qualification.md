# Local Runtime Qualification

GitHub CI proves repository structure, adapter safety, deterministic smoke behavior, and script syntax. It does **not** prove that your installed OpenCode/Pi versions, local model endpoints, tokenizer, or 98,304-token serving configuration behave correctly together.

Use this as the promotion gate for a real local deployment.

## Supported local profile

- model maximum context: **98,304 tokens**;
- normal working target: about **65,536 tokens or less**;
- workflow hard target: about **73,728 tokens or less**;
- reserve: about **24,576 tokens** for tool schemas, evidence variance, reasoning/compaction, and final output;
- Pi: `>=0.85.0`;
- `pi-open-agents`: `>=0.1.20`.

The canonical `liteLLM/...` model names are deployment aliases, not methodology requirements. The default profile currently routes general reviewers through `liteLLM/gpt-oss`, coordinator/final-fact gates through `liteLLM/gemma4`, and the standalone performance auditor through `liteLLM/devstral`. You may point those aliases at different local endpoints as long as the required tool use, context window, and output contracts remain compatible.

## 1. Install and preflight

From this repository:

```bash
scripts/link-opencode-local.sh
scripts/check-canonical-sources.sh
scripts/smoke-opencode-scripts.sh
scripts/smoke-run-artifacts.sh
scripts/preflight-opencode-ping-pong.sh
scripts/preflight-pi-ping-pong.sh
```

Do not proceed if a preflight fails. Fix the runtime or installation rather than weakening the gate.

## 2. Use a fresh artifact root per run

Artifact-backed mode keeps full reviewer reports out of the coordinator's active context.

```bash
export AGENTS_COOKBOOK_RUN_DIR="$PWD/.runs/opencode-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$AGENTS_COOKBOOK_RUN_DIR"
```

The directory must be absolute and fresh. Existing reviewer IDs are never overwritten.

For a Pi qualification run, use a different fresh directory so the exact eight reviewer IDs cannot collide with the OpenCode run.

## 3. Qualify OpenCode

Run one full planning flow against a bounded real repository task:

```bash
opencode run \
  --dir "$PWD" \
  --agent ping-pong-plan \
  --title agents-cookbook-local-qualification \
  --format json \
  "Plan one small, concrete repository improvement. Inspect only evidence needed for the plan and run the complete review flow."
```

Then verify the runtime invocation evidence and the durable artifact store:

```bash
scripts/check-opencode-session.sh --scope latest-segment
scripts/check-run-artifacts.js --run-dir "$AGENTS_COOKBOOK_RUN_DIR"
```

For broader regression coverage, run the fixed benchmark suite separately:

```bash
scripts/run-opencode-benchmarks.js --suite all --repo "$PWD" --artifacts-dir "$PWD/.runs/benchmarks"
```

## 4. Qualify Pi

Start Pi from the target repository, use `/agent` to select `ping-pong-plan`, and send the same bounded planning request.

With `AGENTS_COOKBOOK_RUN_DIR` still pointing at a fresh Pi-specific directory, verify both child behavior and durable evidence:

```bash
scripts/check-pi-session.js --scope latest-turn
scripts/check-run-artifacts.js --run-dir "$AGENTS_COOKBOOK_RUN_DIR"
```

In artifact-backed mode, the Pi session audit requires every successful reviewer child to load its declared skill first and to call `review_artifact` using its own fixed reviewer ID.

## 5. Acceptance criteria

A runtime is qualified only when all of the following are true:

- all eight mandatory reviewers are attempted exactly once and all eight succeed;
- no unexpected reviewer is invoked;
- reviewer authority remains deny-by-default;
- every reviewer produces one immutable artifact and one matching receipt;
- artifact hashes and character counts verify;
- receipt summaries remain within the 1,200-character bound;
- the coordinator uses receipt content by default and does not reproduce raw reviewer reports in the final answer;
- selective `review_artifact_read` is used only when detailed evidence is materially needed;
- the final response satisfies the primary agent's output contract;
- no context overflow, silent truncation, or model-server rejection occurs;
- actual context usage, when exposed by the runtime/model server, stays below the 98,304-token model maximum and should stay below the 73,728-token workflow target.

If actual token usage cannot be measured, record that limitation. Do not claim the 98k deployment profile is empirically qualified solely from character-count gates.

## 6. Fallback mode

If live artifact mode was not enabled for a run, reviewers return their complete reports normally. The run can still be audited and materialized afterward:

```bash
scripts/export-review-artifacts.js --runtime pi --input /path/to/session.jsonl --out runs/<run-id>
scripts/export-review-artifacts.js --runtime opencode --input /path/to/opencode-export.json --out runs/<run-id>
```

Post-run export is an audit/recovery path. It does not provide the live context reduction of `review_artifact` + compact receipts.

## Promotion rule

Do not promote a runtime profile merely because repository CI is green. Promotion requires one successful real OpenCode full-review run and one successful real Pi full-review run on the intended local model configuration, plus the evidence checks above.
