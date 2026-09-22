---
name: baseline-self-authorization-review
description: Finds changes that weaken their own governing baseline or policy and then validate themselves against that candidate state.
license: MIT
---

# Baseline Self-Authorization Review

Standalone, read-only policy/baseline mutation review.

## INVARIANT

> **A candidate change cannot authorize itself by weakening the baseline, threshold, policy, or allowlist used to judge that same change.**

## HUNT

Hunt for same-change mutation of:
- debt or quality baselines;
- coverage floors;
- performance budgets;
- security allowlists;
- compatibility ranges;
- lint/type thresholds;
- policy files or expected snapshots used as the validation oracle.

## PROVE

Show the previous authoritative baseline, the candidate-modified baseline, and the validation command. Demonstrate that a regression passes only because validation reads the candidate's weakened authority instead of comparing candidate policy to the previous authority.

## DO NOT REPORT

Do not report legitimate downward ratchets or policy changes that are independently authorized and explicitly compared against the previous governing baseline.

## PREFER

Bind validation to the previous authoritative baseline first, validate the baseline mutation itself, then evaluate live candidate state against the admitted candidate baseline.

## OUTPUT

Return `# Baseline Self-Authorization Review` with governing baseline, candidate mutation, self-authorization path, independent authority required, corrected validation order, verification.
