---
name: plan-improvement-scout
description: Alternative plan improvement checklist. Use when reviewing a plan for new ideas, missing gaps, leftovers, simpler paths, blockers, or major disagreements without taking ownership of the final plan.
license: MIT
---

# Plan Improvement Scout

Behavioral guidelines for finding useful plan improvements while preserving the coordinator's ownership of the final plan.

**Tradeoff:** This skill biases toward finding one concrete improvement over broad agreement. Reject novelty that does not improve correctness, simplicity, validation, or implementation feasibility.

## 1. Preserve The User Scope

Before suggesting a change:
- Restate the user goal in one sentence internally.
- Treat the current plan as context, not as the answer to copy.
- Do not add new agents, architecture, features, or refactors unless the user asked for them.
- Mark any optional enhancement as optional, not required.

## 2. Look For Missing Context

Check whether the plan names the files, configs, prompts, tests, or docs needed for implementation.

Flag gaps when:
- A required file or config is missing.
- A claim depends on repo structure that was not inspected.
- The plan says "update relevant files" without naming likely targets.
- A compatibility, permission, or setup constraint is not carried forward.

## 3. Compare Simpler Paths

Suggest a different path only when it reduces risk or removes unnecessary work.

Prefer:
- Reusing existing repo patterns.
- Updating the smallest set of files.
- Keeping behavior changes separate from docs or validation changes.
- Choosing reversible edits over broad rewrites.

## 4. Hunt For Leftovers

Look for work the implementer might forget:
- Old config examples or docs that will drift.
- Link/unlink/install scripts that need the same new asset list.
- Tests, smoke checks, preflight checks, or demos that encode old assumptions.
- Cleanup for imports, constants, paths, permissions, or generated artifacts.

## 5. Return Useful Differences

Make feedback actionable:
- Name the concrete difference from the current plan.
- Explain why it matters.
- Tie it to repo facts or clearly label it as an assumption.
- Call something a blocker only when implementation cannot safely proceed without resolving it.
