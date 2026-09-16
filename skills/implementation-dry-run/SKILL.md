---
name: implementation-dry-run
description: Dry-runs implementation for missing steps, ownership, sequencing, feasibility, and validation gaps.
license: MIT
---

# Implementation Dry Run

Standalone, read-only implementation simulation for plans or implementation evidence.

Do not assume a coordinator, Ping-Pong, prior gates, run store, or sibling reviewer. Treat the supplied subject as the simulation input.

## Method

- Walk each material step in order and identify target area, intended behavior, prerequisites, ownership, and proof of completion.
- Verify central repo facts with available read-only tools when useful.
- Flag steps that require guessing, missing assets, ownership conflicts, dependency assumptions, bad sequencing, or infeasible validation.
- Require observable completion criteria where they matter.
- In `BUILD REVIEW MODE`, evaluate supplied implementation evidence instead of producing a replacement plan.
- Never edit files, run commands, invoke agents, provide patches, or claim implementation occurred.

## Output

Normal mode: `# Implementation Simulation Report` with Simulation Outcome (`Implementable`, `Implementable With Fixes`, or `Blocked`); Execution Walkthrough; Missing Or Ambiguous Steps; File / Ownership Risks; Validation Gaps; Concrete Fix Suggestions; Repo Facts Used.

Each issue includes severity, affected step, problem, impact, and suggested fix.

Build mode: `# Build Review Report` with Blocking Findings; Non-Blocking Findings; Missing Validation; Suggested Fixes; Evidence Inspected; Confidence / Remaining Risk.

Use `None` for empty sections.
