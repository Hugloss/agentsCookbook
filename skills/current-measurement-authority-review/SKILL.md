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

Compare the historical/baseline source with an executable current observation and show a materially different result, ranking, or selected target while code still treats the baseline as current truth.

## DO NOT REPORT

Do not report a baseline used only as a no-growth constraint, acceptance threshold, or historical comparison when current measurement remains separate.

## PREFER

Separate baseline authority from live observation authority. Measure current state explicitly, bind its tool/config/source identity, then compare it to the baseline.

## OUTPUT

Return `# Current Measurement Authority Review` with claimed current fact, stale authority source, current observation, divergence, decision impact, correction, and verification.
