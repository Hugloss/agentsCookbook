# Ping-Pong Plan Benchmarks

Use these manual benchmarks to judge whether `ping-pong-plan` improves production planning quality.

The benchmark harness is intentionally Markdown-only. It does not add an agent, command, or runtime dependency. Run a benchmark by giving the user request to `ping-pong-plan`, then score the final `MASTER PLAN` with the rubric below.

For repeatable local replays, use `scripts/run-opencode-benchmarks.js`. That script keeps the manual rubric here, but it gives you a fast loop for rerunning the fixed benchmark set, capturing session IDs, and checking the resulting sessions with `scripts/check-opencode-session.sh`.

## Scorecard

Score each category from 1 to 5.

| Category | 1 | 3 | 5 |
| --- | --- | --- | --- |
| Decision completeness | Leaves major implementation choices unresolved. | Some defaults and file targets are concrete, but a few choices remain vague. | No implementation decision is left to the implementer. |
| Repo grounding | Uses guessed files, commands, or architecture. | Mixes verified facts with assumptions that are mostly labeled. | Uses structured context and clearly separates repo facts, assumptions, unknowns, and not-inspected areas. |
| Validation quality | Validation is missing, vague, or infeasible. | Includes plausible checks but misses observable acceptance criteria or rollback verification. | Includes concrete automated checks, manual checks, observable pass/fail acceptance criteria, failure cases, and rollback verification. |
| Scope control | Adds unrelated refactors or optional work as required work. | Mostly scoped, with minor optional work not clearly separated. | Required work exactly matches user intent; optional work is clearly separated. |
| Implementability | An engineer would need to redesign or investigate before starting. | Implementable with some extra interpretation. | Ready to hand to an implementer as-is. |

## Automatic Fail Conditions

Fail the benchmark regardless of numeric score if the final plan:

- contains unsupported repo claims presented as facts
- contains implementation-blocking open questions
- leaks raw subagent reports, Decision Ledgers, or internal process notes
- leaks the internal Intent Contract as a standalone artifact
- omits or fails to use structured `KNOWN CONTEXT` headings in subagent payloads when reviewing the flow itself
- uses vague steps such as "update relevant tests" without concrete targets
- omits validation, observable pass/fail acceptance criteria, or rollback / recovery guidance
- ignores severe gate findings such as `Insufficient`, `Blocking Issues`, `Blocked`, or `Fail` without a repo-fact or user-scope reason
- delegates canonical plan ownership to a subagent
- expands scope beyond the user's request without marking it optional
- skips a reviewer because model 1 performed similar analysis directly
- reports reviewer success without a matching runtime delegation event

## Benchmark 1: Skill / Agent Edit

### User Request

Improve the `plan-contract-guard` skill so `plan-contract-checker` fails final plans with implementation-blocking open questions. Do not add another agent.

### Expected Inspected Areas

- `.agents/skills/plan-contract-guard/SKILL.md`
- `.opencode/agents/plan-contract-checker.md`
- `.opencode/agents/ping-pong-plan.md`
- `opencode.json`

### Expected Plan Qualities

- Identifies the checker skill as the primary change area.
- Keeps model 1 as the only canonical plan author.
- Preserves the internal Intent Contract and Decision Ledger as hidden process artifacts.
- Adds no new subagent.
- Includes validation for JSON parsing, diff hygiene, and OpenCode agent resolution.
- Separates skill-contract changes from agent wiring changes.

## Benchmark 2: Flow Documentation

### User Request

Create documentation that explains the ping-pong planning flow, all agents, and the final plan ownership rules.

### Expected Inspected Areas

- `.opencode/agents/ping-pong-plan.md`
- `.opencode/agents/`
- `.agents/skills/`
- `opencode.json`
- existing `.opencode` documentation files

### Expected Plan Qualities

- Chooses a docs-only path unless repo facts show a behavior change is needed.
- Documents the ordered flow, read-only permissions, no-leak rule, and final output contract.
- Documents structured `KNOWN CONTEXT`, severe gate handling, and pass/fail acceptance criteria.
- Does not duplicate full skill text.
- Includes a lightweight validation plan for Markdown coverage and whitespace.

## Benchmark 3: Permission Audit

### User Request

Review whether all ping-pong subagents have permissions that match their read-only roles, and plan fixes for any mismatch.

### Expected Inspected Areas

- `opencode.json`
- `.opencode/agents/ping-pong-plan.md`
- all reviewer files in `.opencode/agents/`
- all reviewer contracts in `.agents/skills/`
- `opencode debug agent` output when validation is allowed

### Expected Plan Qualities

- Compares agent and skill tool rules against resolved OpenCode permissions.
- Flags any subagent, bash, edit, web, question, or external-directory mismatch.
- Keeps coordinator permissions distinct from subagent permissions.
- Includes validation by resolving every configured agent.

## Benchmark 4: Validation Hardening

### User Request

Make the planning flow stricter about validation quality and rollback verification without adding more agents.

### Expected Inspected Areas

- `.opencode/agents/ping-pong-plan.md`
- `.agents/skills/validation-gap-finder/SKILL.md`
- `.agents/skills/plan-contract-guard/SKILL.md`
- `.agents/skills/implementation-dry-run/SKILL.md`

### Expected Plan Qualities

- Strengthens existing validation-related rules instead of creating a new agent.
- Requires concrete commands or clearly marked assumptions.
- Requires observable pass/fail acceptance criteria, manual checks when needed, failure scenarios, and rollback verification.
- Blocks advancement on `Insufficient`, `Blocking Issues`, `Blocked`, or `Fail` gate outcomes unless contradicted by repo facts or user scope.
- Makes final-plan validation decision-complete.

## Benchmark 5: Multi-Skill Review Refactor

### User Request

Update the ping-pong flow so subagents independently verify central repo claims instead of relying only on coordinator context.

### Expected Inspected Areas

- `.opencode/agents/ping-pong-plan.md`
- `.agents/skills/plan-improvement-scout/SKILL.md`
- `.agents/skills/validation-gap-finder/SKILL.md`
- `.agents/skills/red-team-leftover-gate/SKILL.md`
- `.agents/skills/implementation-dry-run/SKILL.md`
- `.agents/skills/fact-grounding-auditor/SKILL.md`
- `.agents/skills/plan-contract-guard/SKILL.md`

### Expected Plan Qualities

- Adds read-only spot-check requirements to existing skills.
- Preserves the structured `KNOWN CONTEXT` format in first-round and convergence calls.
- Does not permit subagents to edit, run bash, invoke subagents, or own the final plan.
- Requires unverifiable claims to be labeled as assumptions, missing evidence, risks, or blockers.
- Includes validation that no new agent was added.

## Benchmark 6: Complementary Improvers

### User Request

Find N+1 database lookups in inner loops and plan a bulk-loading refactor without changing behavior.

### Expected Plan Qualities

- Calls all eight reviewers rather than finishing after the coordinator's repository scan.
- Uses `plan-improver-model2` to identify omissions, leftovers, ownership, and validation that the draft missed.
- Uses `plan-improver-model3` to challenge assumptions and test a genuinely different implementation route.
- Preserves useful master-plan findings if one attempted reviewer call fails, then continues attempting later gates.
- Never uses "analysis was performed by model 1" as a skip reason.
- Passes the runtime session checker; prose-only success claims do not count.

## Review Notes Template

Use this template after each run.

```md
# Ping-Pong Benchmark Review

## Benchmark

<benchmark name>

## Scores

- Decision completeness:
- Repo grounding:
- Validation quality:
- Scope control:
- Implementability:

## Automatic Fail Conditions

<None, or list failures>

## Strongest Plan Qualities

<short notes>

## Weakest Plan Qualities

<short notes>

## Skill / Flow Fixes Suggested

<short notes>
```
