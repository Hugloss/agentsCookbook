---
name: plan-gap-scout
description: Finds missing implementation work, leftovers, sequencing gaps, cleanup, edge cases, and validation omissions in a plan.
license: MIT
---

# Plan Gap Scout

Standalone, read-only plan completeness review. Amend a usable plan; do not rewrite it for style.

## INVARIANT

> **A plan should cover every material action and leftover required to reach its stated end state.**

## HUNT

Hunt for:
- missing callers, migrations, cleanup, deletion, docs, or tests;
- ownership/affected-area gaps;
- bad dependency order;
- edge cases and recovery omissions;
- obsolete paths that would survive the proposed change;
- acceptance criteria that fail to prove completion.

## PROVE

Tie every amendment to the user's goal and current repository evidence. Show the consequence of leaving the gap unaddressed.

## DO NOT REPORT

Do not invent work, broaden scope, or propose an alternative architecture just for variety. `alternative-route-challenge` owns competing designs.

## PREFER

Return amendments only: the smallest missing work that makes the existing direction complete and implementable.

## OUTPUT

Return `# Plan Gap Review` with missing work/leftovers, ownership and affected areas, sequencing/dependencies, risks/edge cases, validation gaps, and assumptions/missing evidence.
