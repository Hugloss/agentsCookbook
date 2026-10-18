# Local Runtime Qualification

Cookbook CI proves repository structure, adapter safety, deterministic smoke behavior, and script syntax. [EvalShot](https://github.com/Hugloss/EvalShot) owns corpus validation and executable benchmarks. Neither repository's model-free checks prove that your installed OpenCode/Pi versions, local model endpoints, actual tokenizer/context configuration, or specialist discrimination behave correctly together.

Use this as the promotion gate for a real local deployment.

## Host compatibility and context selection

- Pi: `>=0.85.0`;
- `pi-open-agents`: `>=0.1.20`.

The canonical `liteLLM/...` model names are deployment aliases, not methodology
requirements. The default reviewer aliases may be mapped to different
local endpoints that support their required tools and output contracts.

Agents Cookbook owns adapter setup, review-flow behavior and direct host-session
checks. The operator configures the runtime context window. EvalShot owns
[concrete context profiles, limits and measurement qualification](https://github.com/Hugloss/EvalShot/blob/main/docs/context-profiles.md).
No numeric context profile is required to install or preflight the reusable
cookbook prompts.

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

Do not proceed if a preflight contract fails. Fix the runtime, installation, or canonical sources before claiming the local profile is qualified. Validate the evaluation corpus through EvalShot when performing behavioral qualification in step 5.

## 2. Use a fresh artifact root per run

Artifact-backed mode keeps full reviewer reports out of the coordinator's active context.

For OpenCode:

```bash
export AGENTS_COOKBOOK_RUN_DIR="$PWD/.runs/opencode-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$AGENTS_COOKBOOK_RUN_DIR"
```

The directory must be absolute and fresh. Existing reviewer IDs are never overwritten.

Use a different fresh directory for Pi so the exact nine reviewer IDs cannot collide with the OpenCode run.

## 3. Qualify OpenCode full flow

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

For broader regression coverage, use the [flow benchmark runner in EvalShot](https://github.com/Hugloss/EvalShot/blob/main/evals/README.md) with an explicit cookbook checkout. Unset `AGENTS_COOKBOOK_RUN_DIR` before that benchmark and use its own evidence directory. A live artifact root must be unique per review run because reviewer artifact IDs are intentionally create-only.

## 4. Qualify Pi full flow

Create a fresh Pi-specific artifact root:

```bash
export AGENTS_COOKBOOK_RUN_DIR="$PWD/.runs/pi-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$AGENTS_COOKBOOK_RUN_DIR"
```

Start Pi from the target repository, use `/agent` to select `ping-pong-plan`, and send the same bounded planning request.

Then verify both child behavior and durable evidence:

```bash
scripts/check-pi-session.js --scope latest-turn
scripts/check-run-artifacts.js --run-dir "$AGENTS_COOKBOOK_RUN_DIR"
```

In artifact-backed mode, the Pi session audit requires every successful reviewer child to load its declared skill first and to call `review_artifact` using its own fixed reviewer ID.

Pi's subagent wrapper returns the child `result.output` as parent-visible tool text while retaining child tool traces separately in result details. The qualification run should therefore show compact receipt output returning to the coordinator rather than the full reviewer report.

## 5. Qualify sharp specialist discrimination

Install/discovery and full-flow success do not prove that a narrow skill keeps its edge. Run the canonical positive/control/confusion corpus in [EvalShot](https://github.com/Hugloss/EvalShot/tree/main/evals) against the intended local model profile and the exact cookbook checkout being promoted.

Follow [EvalShot's sharp skill discrimination guide](https://github.com/Hugloss/EvalShot/blob/main/evals/sharp-skill-discrimination.md) for corpus validation, `--cookbook-root` selection, OpenCode/Pi execution, and artifact paths. Start with high-overlap specialists such as `stale-work-race-review`, `durable-commit-path-review`, and `retry-idempotency-review`, then run the full corpus when promoting a profile intended to use all specialists. Keep benchmark artifacts separate from the full-flow artifact roots used above.

A specialist is behaviorally qualified only when its positive cases produce in-scope findings, its control cases stay clean, and its confusion cases refuse neighboring failure classes. The runner requires concise evidence for every verdict and records elapsed time/output size per case.

Do not compare OpenCode and Pi by exact prose. Compare verdict, scope, evidence quality, false-positive behavior, and runtime/context economics.

## 6. Acceptance criteria

A runtime/profile is qualified only when the relevant claims below are true:

- all nine mandatory reviewers are attempted exactly once and all nine succeed in the full flow;
- no unexpected reviewer is invoked;
- reviewer authority remains deny-by-default;
- every reviewer produces one immutable artifact and one matching receipt;
- artifact hashes and character counts verify;
- receipt summaries remain within the 1,200-character bound;
- the coordinator uses receipt content by default and does not reproduce raw reviewer reports in the final answer;
- selective `review_artifact_read` is used only when detailed evidence is materially needed;
- the final response satisfies the primary agent's output contract;
- every specialist claimed as qualified passes its positive and control cases;
- confusion cases pass for the high-overlap skill boundaries being promoted;
- no context overflow, silent truncation, or model-server rejection occurs;
- actual context usage, when exposed by the runtime/model server, remains within the configured model and host limits; any numerical target claimed for a tested profile is qualified in EvalShot.

If actual token usage cannot be measured, record that limitation. Do not claim that a model-specific context profile is empirically qualified solely from character-count gates.

## 7. Fallback mode

If live artifact mode was not enabled for a run, reviewers return their complete reports normally. The run can still be audited and materialized afterward:

```bash
scripts/export-review-artifacts.js --runtime pi --input /path/to/session.jsonl --out runs/<run-id>
scripts/export-review-artifacts.js --runtime opencode --input /path/to/opencode-export.json --out runs/<run-id>
```

Post-run export is an audit/recovery path. It does not provide the live context reduction of `review_artifact` + compact receipts.

## Promotion rule

Do not promote a runtime profile merely because repository CI is green. Promotion requires one successful real OpenCode full-review run and one successful real Pi full-review run on the intended local model configuration, plus the evidence checks above. Any specialist advertised as qualified must also have model-backed discrimination results for that runtime/profile.
