---
name: alternative-route-challenge
description: Challenges a plan or implementation with a materially different repository-grounded route when evidence supports one.
license: MIT
---

# Alternative Route Challenge

Standalone, read-only adversarial design review.

## INVARIANT

> **A useful alternative must change a material assumption or execution route, not merely rename the current approach.**

## HUNT

Hunt for central assumptions that create avoidable:
- duplication;
- migration burden;
- sequencing risk;
- ownership leakage;
- compatibility work;
- irreversible choices.
Look for a simpler or safer route already supported by repository structure.

## PROVE

Explain the challenged assumption, repository evidence, alternative route, tradeoffs, and major disagreement with the current direction. Show why the route is genuinely different.

## DO NOT REPORT

Do not manufacture disagreement for reviewer diversity. If the current route is already strongest, say so. Do not drift beyond user scope.

## PREFER

Prefer alternatives that delete work, preserve coherent boundaries, or establish a stronger invariant with fewer steps.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, challenge only material implementation choices that can still be corrected. Do not propose a rewrite merely because another design is aesthetically different.

Return `# Build Alternative Review` with blocking findings, non-blocking findings, a materially better route if one is proved, concrete fixes, and remaining risk. Use `None` when the implemented route should stand.

## OUTPUT

Otherwise return `# Alternative Plan` with goal, challenged assumptions, steps, affected areas, evidence, tradeoffs/risks, validation, recovery, key differences, and blockers or major disagreements.
