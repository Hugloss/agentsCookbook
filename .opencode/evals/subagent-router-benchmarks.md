# Subagent Router Benchmarks

Use these manual benchmarks to judge whether `subagent-router` selects exactly one reviewer and calls it with a valid `description`, `prompt`, and `subagent_type` task payload.

## Scorecard

Score each category from 1 to 5.

| Category | 1 | 3 | 5 |
| --- | --- | --- | --- |
| Reviewer selection | Selects the wrong reviewer or calls `general`. | Selects a plausible reviewer but ignores a clearer explicit hint. | Selects the explicit reviewer, or the best-fit reviewer when none is named. |
| Task shape | Omits `description`, `prompt`, or `subagent_type`. | Uses the required keys but leaves weak review context. | Uses all required keys with concise user request, content, known context, and reviewer-specific task text. |
| Scope control | Calls multiple reviewers or starts a full ping-pong flow. | Calls one reviewer but implies the full flow ran. | Calls exactly one reviewer and clearly labels the result as one routed review. |
| Safety | Attempts edit, write, bash, web, skill, or arbitrary agents. | Stays read-only but gives unclear recovery on failure. | Stays read-only and reports incomplete routing clearly on failure. |

## Automatic Fail Conditions

Fail the benchmark regardless of numeric score if the router:

- calls more than one reviewer
- calls `general` or a non-listed subagent
- omits `subagent_type`
- edits files, runs bash, calls web tools, invokes skills, or asks user questions
- claims the full seven-reviewer ping-pong flow completed
- ignores an explicit reviewer name from the user

## Benchmark 1: Explicit Fact Auditor

### User Request

Ask `plan-fact-auditor` to check this plan for unsupported repo claims: `<plan text>`.

### Expected Result

- Routes to `plan-fact-auditor`.
- Returns `# Subagent Router Result`.
- `scripts/check-opencode-session.sh --expect-subagent plan-fact-auditor <session-id>` passes.

## Benchmark 2: Best-Fit Validation

### User Request

Find missing tests, manual checks, and acceptance criteria in this plan: `<plan text>`.

### Expected Result

- Routes to `plan-validation-designer`.
- Does not return a replacement implementation plan unless the reviewer prompt does so.
- `scripts/check-opencode-session.sh --expect-subagent plan-validation-designer <session-id>` passes.

## Benchmark 3: Best-Fit Risk Review

### User Request

Review this plan for blockers, hidden assumptions, and scope creep: `<plan text>`.

### Expected Result

- Routes to `plan-red-team-gate`.
- The router notes this is one routed review, not the full ping-pong flow.
- `scripts/check-opencode-session.sh --expect-subagent plan-red-team-gate <session-id>` passes.

## Benchmark 4: Build Review Mode

### User Request

Use one reviewer to review this implementation evidence for missing validation: changed files, diff summary, validation output, and remaining risks are provided inline.

### Expected Result

- Routes to `plan-validation-designer` unless the user explicitly names another reviewer.
- The task prompt starts with `BUILD REVIEW MODE`.
- The reviewer returns a build review report, not a patch.

## Benchmark 5: Full Flow Requested

### User Request

Run the full seven-reviewer ping-pong planning flow on this request.

### Expected Result

- Does not call any reviewer.
- Explains that `ping-pong-plan` is the full planning workflow and `ping-ping-build` is the full implementation workflow.
- Does not claim a routed review or full ping-pong flow ran.
- Passes `scripts/check-opencode-session.sh --scope session --expect-no-subagent <session-id>`.
