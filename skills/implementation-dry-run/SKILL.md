---
name: implementation-dry-run
description: Dry-runs a plan against the repository to expose missing steps, ownership, sequencing, feasibility, and proof gaps.
license: MIT
---

# Implementation Dry Run

Standalone, read-only implementation simulation. Walk the proposed work as if implementing it now.

## INVARIANT

> **A plan is implementable only when a developer can execute it without guessing material behavior, ownership, order, or proof.**

## HUNT

For every material step hunt for:
- missing target files/areas or prerequisites;
- ownership conflicts and hidden dependencies;
- impossible or unsafe sequencing;
- missing cleanup and leftover paths;
- completion criteria that cannot be observed.

## PROVE

Walk the steps in order against current repository evidence. Show exactly where implementation would have to guess or where the proposed sequence breaks.

## DO NOT REPORT

Do not redesign a usable plan merely to prefer another style. Do not claim implementation or validation was executed. In BUILD REVIEW MODE, simulate the supplied implementation evidence instead of requiring plan-shaped sections.

## PREFER

Add the smallest missing step, prerequisite, ordering constraint, or proof needed to make execution deterministic.

## OUTPUT

Return `# Implementation Simulation Report` with outcome, execution walkthrough, missing/ambiguous steps, ownership risks, validation gaps, and concrete fixes. Each issue: severity, affected step, problem, impact, fix.
