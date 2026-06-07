---
name: red-team-leftover-gate
description: Risk and leftover review checklist. Use when looking for blockers, hidden risks, scope creep, stale assumptions, missed cleanup, or unsafe plan content before finalizing a plan or implementation.
license: MIT
---

# Red-Team Leftover Gate

Behavioral guidelines for finding concrete risks before a plan or implementation is treated as ready.

**Tradeoff:** This skill biases toward catching costly misses over preserving wording. Do not turn style preferences into blockers.

## 1. Find Real Blockers

Call something blocking only when it can make the work unsafe, incomplete, or impossible.

Examples:
- A required config path is unknown.
- Permissions contradict the intended tool use.
- A plan tells a read-only agent to edit files.
- Acceptance criteria are absent and completion cannot be judged.

## 2. Challenge Hidden Assumptions

Look for claims the plan treats as facts without evidence:
- Default OpenCode discovery paths.
- Permission behavior.
- Existing scripts or tests.
- Whether a target repo has copied the example config.

Ask for evidence in the plan, not broad research.

## 3. Catch Scope Creep

Flag required work that does not serve the user request:
- New agents when existing agents are enough.
- Broad prompt rewrites when a small rule is enough.
- New runtime dependencies for static Markdown skills.
- Refactors not needed for skill discovery or validation.

## 4. Inspect Leftovers

Search for stale references after a proposed change:
- Docs that mention only agents and prompts.
- Scripts that link or unlink only old asset types.
- Preflight checks that do not validate new assets.
- Examples with outdated permission blocks.

## 5. Suggest Safe Fixes

Every issue should include a low-risk fix:
- Keep the same ownership model.
- Touch the smallest file set.
- Make rollback obvious.
- Prefer explicit names over "as needed" instructions.
