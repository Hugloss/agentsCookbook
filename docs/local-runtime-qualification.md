# Local Runtime Qualification

Cookbook CI checks repository structure, bounded adapter behavior, deterministic
failure cases, and script syntax. [EvalShot](https://github.com/Hugloss/EvalShot)
owns corpus validation and executable benchmarks. Neither repository's model-free
checks prove that your installed OpenCode/Pi versions, local model endpoints,
actual tokenizer/context configuration, or specialist discrimination behave
correctly together.

Use this as the promotion gate for a real local deployment. It qualifies a
particular host/model profile; it is not a prerequisite for authoring,
installing, or using a canonical skill. For contribution checks, follow
[evaluation ownership and evidence](../CONTRIBUTING.md#evaluation-ownership-and-evidence).

## Host compatibility and context selection

The checked Pi integration profile is `@earendil-works/pi-coding-agent` **1.4.0**
with `pi-open-agents` **0.1.26**. Native model-free loading, permission/delegation
checks, and skill/artifact I/O passed for that pair on 2026-10-30. This is not a
model-backed deployment qualification. Older and newer versions require their
own compatibility review; the former open-ended minimum version claims are
removed.

`pi-open-agents` **0.1.27** fails this composition because its inherited wildcard
deny removes explicitly allowed child tools, and its parent ceiling cannot
grant the reviewer-only artifact sink. Preflight reports that incompatibility;
it never disables native inheritance or changes installed packages. See the
[Pi adapter's checked profile and upstream sources](../adapters/pi/README.md#checked-host-profile).
These integration limits do not restrict using standalone canonical skills.

The canonical agents contain no model, temperature, or reasoning defaults.
Select the model and inference options through the native host configuration.
The selected model must support the role's tools and output contract; the
cookbook does not silently choose a different deployment.

Agents Cookbook owns adapter setup, review-flow behavior and direct host-session
checks. The operator configures the model context window and compaction in the chosen
model provider/host, where supported. See the [OpenCode provider settings](https://docs.opencode.ai/docs/providers/).
[EvalShot](https://github.com/Hugloss/EvalShot/blob/main/docs/model-context-observation.md)
can measure actual context behavior, but neither repository mandates a model-specific
context size to install, preflight or use reusable prompts.

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

Use the supported OpenCode 1.x adapter and run full preflight first. OpenCode 2
requires a plugin/API migration and is not qualified by these commands. A passing
`--quick` preflight checks source links only; it does not inspect native tool
authority. See the [adapter compatibility boundary](../adapters/opencode/README.md#runtime-compatibility).

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

The session check requires completed, nonempty reviewer results and matching
native identities. Failed/pending calls, background launch acknowledgements and
damaged exports cannot satisfy the gate. Scoped checks require the SQLite
timeline; use an explicit session ID with `--scope session` only when intentionally
qualifying the entire exported session. Artifact reads also verify each report
against its receipt before presenting the text to the coordinator.

For broader regression coverage, use the [flow benchmark runner in EvalShot](https://github.com/Hugloss/EvalShot/blob/main/evals/README.md) with an explicit cookbook checkout. Unset `AGENTS_COOKBOOK_RUN_DIR` before that benchmark and use its own evidence directory. A live artifact root must be unique per review run because reviewer artifact IDs are intentionally create-only.

## 4. Qualify Pi full flow

First verify the native package declaration and the exact checked pair:

```bash
scripts/preflight-pi-ping-pong.sh
```

The preflight reads `settings.packages`, including supported source objects and
project package overrides; it does not infer npm enablement from a string in
`settings.extensions`. If auditing another candidate version, use
`scripts/check-pi-native-compatibility.js --help` to run a model-free probe against
explicitly supplied package directories before updating the compatibility gate.

Create a fresh Pi-specific artifact root:

```bash
export AGENTS_COOKBOOK_RUN_DIR="$PWD/.runs/pi-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$AGENTS_COOKBOOK_RUN_DIR"
```

Start Pi from the target repository, use `/agent` to select `ping-pong-plan`, and
send the same bounded planning request. For this auditable profile, add:

```text
For this qualification run, pass session: "fork" on every native subagent call
so its linked child session and successful tool results can be audited.
```

`pi-open-agents` 0.1.26 reports the child session file for native forked sessions.
Its default fresh-session result does not expose that link. The checker leaves
fresh-session tool outcomes unknown instead of guessing a child file by time or
reporting the wrapper's `done` status as success. Forking copies parent context;
this run qualifies the forked-session profile and its observed context cost,
not the default fresh-session profile.

Then verify both child behavior and durable evidence:

```bash
scripts/check-pi-session.js --scope latest-turn
scripts/check-run-artifacts.js --run-dir "$AGENTS_COOKBOOK_RUN_DIR"
```

In artifact-backed mode, the Pi session audit requires evidence that every
successful reviewer child loaded its declared skill first and saved
`review_artifact` using its own fixed reviewer ID. The wrapper's child trace
marks a tool `done` when it ends even if the tool failed; that marker is evidence
of completion, not a successful skill read or save. Full qualification therefore
requires linked native child tool results as well as the durable artifact check.

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
- observed context usage and compaction, when exposed by the runtime/model server, are recorded against the selected runtime/model configuration; no cookbook token-window threshold is enforced.

If actual token usage cannot be measured, record that limitation. Character-count checks must not be used as proof of token-window compliance.

## 7. Fallback mode

If live artifact mode was not enabled for a run, reviewers return their complete reports normally. The run can still be audited and materialized afterward:

```bash
scripts/export-review-artifacts.js --runtime pi --input /path/to/session.jsonl --out runs/<run-id>
scripts/export-review-artifacts.js --runtime opencode --input /path/to/opencode-export.json --out runs/<run-id>
```

Post-run export is an audit/recovery path. It does not provide the live context reduction of `review_artifact` + compact receipts.

## Promotion rule

Do not promote a runtime profile merely because repository CI is green. Each
OpenCode or Pi profile being promoted needs a successful real full-review run
on its intended model configuration, plus the evidence checks above. A claim of
support for both hosts needs those results for both. Any specialist advertised
as qualified also needs model-backed discrimination results for that profile.
