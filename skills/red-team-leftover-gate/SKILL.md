---
name: red-team-leftover-gate
description: Finds concrete blockers, hidden risk, stale assumptions, leftovers, and scope creep before handoff.
license: MIT
---

# Red-Team Leftover Gate

Standalone, read-only adversarial gate for plans, changes, implementation evidence, or direct risk questions.

## INVARIANT

> **No material blocker should survive because everyone assumed another layer handled it.**

## HUNT

Hunt for:
- unsafe, incomplete, or infeasible work;
- stale paths, permissions, dependencies, or discovery assumptions;
- sequencing/ownership gaps;
- missing validation or recovery;
- leftovers and parallel paths;
- scope creep that changes the requested problem.

## PROVE

A blocker must have a concrete failure mode and evidence. Explain location, impact, and the lowest-risk correction.

## DO NOT REPORT

Do not produce generic warnings, duplicate non-blocking style feedback, or label uncertainty as blocking without showing how it prevents safe completion.

## PREFER

Block only material risk. Keep corrections narrow and evidence-driven.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, anchor every finding in changed files, supplied evidence, or a production path affected by the change. Hunt especially for surviving old paths, stale authority, incomplete cleanup, and unproved failure behavior.

Return `# Build Red-Team Review` with blocking findings, non-blocking findings, missing validation/evidence, concrete fixes, and remaining risk. Use `None` when clean.

## OUTPUT

Otherwise return `# Red-Team Gate Report` with blocking issues, high-risk ambiguities, missing validation, scope creep, concrete fixes, and repo facts used. Use `None` when clean.
