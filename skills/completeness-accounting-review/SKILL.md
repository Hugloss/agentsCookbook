---
name: completeness-accounting-review
description: Finds complete/success claims that fail to account for every expected unit, including missing, excluded, malformed, or truncated work.
license: MIT
---

# Completeness Accounting Review

Standalone, read-only completeness review.

## INVARIANT

> **A result is complete only when every expected unit is explicitly accounted for.**

## HUNT

Hunt in scans, pagination, streams, batches, shards, parsers, indexes, and evidence collectors for:
- EOF or missing-final-newline assumptions;
- pagination termination without total accounting;
- swallowed parse failures or skipped members;
- truncation that still reports complete;
- expected units disappearing between selected, attempted, processed, excluded, missing, malformed, and failed counts;
- zero failures being treated as proof of complete coverage.

## PROVE

Establish the expected universe and reconcile it against terminal categories. Show the unaccounted unit or contradictory counters and the code path that can still emit complete/success.

## DO NOT REPORT

Do not report intentionally best-effort output that is explicitly marked partial, unknown, or truncated and is not reused as complete evidence.

## PREFER

Use explicit terminal categories, bounded counters, and a conservation check before setting completeness.

## OUTPUT

Return `# Completeness Accounting Review` with expected universe, accounting table, unaccounted units, false completion path, correction, and verification.
