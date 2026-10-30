---
name: current-measurement-authority-review
description: Finds historical baselines, snapshots, budgets, or ratchets reused as if they were executable measurements of current repository or runtime state.
license: MIT
---

# Current Measurement Authority Review

Standalone, read-only measurement-source review.

## INVARIANT

> **A claim about current state must come from a current observation; historical baselines and ratchets constrain change but do not measure present reality.**

## HUNT

Hunt for:
- debt baselines sorted as current hotspots;
- expected snapshots reused as live inventory;
- budgets treated as observed usage;
- last-run metrics reused without freshness proof;
- cached reports selecting current work after source/tool/config drift;
- current improvement claims derived only from historical threshold files.

## PROVE

Trace the claim of currentness and its freshness/identity guard. Prove either a materially different current result, ranking, or selected target, or a reachable reuse after a relevant source/tool/configuration change without evidence that the observation remains current. In the latter case report unsupported authority, not an invented measured difference. A cached observation remains admissible when its binding proves the relevant state is unchanged.

## DO NOT REPORT

Do not report a baseline used only as a no-growth constraint, acceptance threshold, or historical comparison when current measurement remains separate.

## PREFER

Separate baseline authority from live observation authority. Measure current state explicitly, bind its tool/config/source identity, then compare it to the baseline.

## OUTPUT

Return `# Current Measurement Authority Review` with claimed current fact, stale authority source, current observation, divergence, decision impact, correction, and verification.

Use `FINDING` for a demonstrated stale-as-current authority path; distinguish a false current result from unsupported currentness. Bound `CLEAN` to inspected observations and freshness guards. If missing evidence prevents establishing either admissible reuse or a guard violation, return `INSUFFICIENT EVIDENCE`.
