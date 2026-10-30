---
name: implementation-dry-run
description: Dry-runs planned or completed work to expose missing steps, ownership, sequencing, feasibility, and proof gaps.
license: MIT
---

# Implementation Dry Run

Standalone, read-only implementation simulation. Walk the proposed or completed work as if responsible for shipping it now.

## INVARIANT

> **A change is implementable only when execution does not require guessing material behavior, ownership, order, or proof.**

## HUNT

For every material step hunt for:
- missing target files/areas or prerequisites;
- ownership conflicts and hidden dependencies;
- impossible or unsafe sequencing;
- missing cleanup and leftover paths;
- completion criteria that cannot be observed.

## PROVE

State the inspected change boundary and walk its material steps in order against current repository evidence, including prerequisites, callers and observable completion. Show exactly where implementation would have to guess a product/ownership contract or where the proposed sequence breaks. An unavailable target is missing evidence; a verified missing prerequisite that the step requires to exist already, or an incompatible prerequisite, is a concrete issue. A planned new file/module is valid when its creation, parent/owner and prerequisites are accounted for. Do not invent files, commands, helper APIs or execution results to bridge an actual gap.

## DO NOT REPORT

Do not redesign a usable direction merely to prefer another style. Routine implementation choices, such as local names or an equivalent algorithm satisfying an explicit contract, need not be prescribed. Do not claim implementation or validation was executed unless evidence proves it.

## PREFER

Add the smallest missing step, prerequisite, ordering constraint, cleanup, or proof needed to make execution deterministic.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, replay the supplied implementation path rather than demanding a plan. Check whether changed files, callers, cleanup, ordering, and validation form a complete shippable sequence.

Return `# Build Implementation Simulation` with inspected scope, blocking findings, non-blocking findings, missing steps/cleanup, missing validation/evidence, concrete fixes, and remaining risk. Use `None` only when all material steps and dependencies within that scope can be traced without unresolved contract assumptions; otherwise mark the unresolved part `INSUFFICIENT EVIDENCE`.

## OUTPUT

Otherwise return `# Implementation Simulation Report` with outcome, inspected scope, execution walkthrough, missing/ambiguous steps, ownership risks, validation gaps, and concrete fixes. Each issue: severity, affected step, problem, impact, fix. Keep established issues alongside unresolved steps. A complete simulation establishes implementability within that boundary, not successful execution.
