---
name: bounded-authority-monotonicity-review
description: Finds authoritative conclusions that oscillate when only retrieval, pagination, top-k, or presentation bounds change.
license: MIT
---

# Bounded Authority Monotonicity Review

Standalone, read-only bounded-evidence authority review.

## INVARIANT

> **Changing a presentation or retrieval bound must not revoke or replace already-proven authority unless newly admitted authoritative evidence changes the proof.**

## HUNT

Hunt for authority coupled to:
- top-k, limit, per-role, page size, pagination, batch size, or compact-view bounds;
- truncation order;
- first-page candidate sets;
- display ranking or bounded alternatives;
- retries that expose more presentation rows without changing the proof universe.

## PROVE

Run the same semantic request across at least two bounds. Candidate visibility may change. If the authoritative conclusion changes, identify the newly admitted evidence that legitimately changed proof; otherwise prove bound-driven oscillation.

## DO NOT REPORT

Do not report changes to candidate lists, rankings, diagnostics, or explicitly bounded presentation when the authority result remains stable.

## PREFER

Separate the complete proof scope from bounded presentation and record presentation completeness independently.

## OUTPUT

Return `# Bounded Authority Monotonicity Review` with bound variants, proof scope, authority outcomes, newly admitted evidence if any, violation, correction, verification.
