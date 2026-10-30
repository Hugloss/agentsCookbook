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

Establish the expected universe from the operation contract, selection, or source membership independently of the surviving result rows, then reconcile each unit against terminal categories without double counting. Show the unaccounted unit or contradictory counters and the code path that can still emit complete/success. Accounted-for failure or exclusion can establish completeness but cannot establish success unless the success contract permits it.

## DO NOT REPORT

Do not report intentionally best-effort output that is explicitly marked partial, unknown, or truncated and is not reused as complete evidence.

## PREFER

Use explicit terminal categories, bounded counters, and a conservation check before setting completeness.

## OUTPUT

Return `# Completeness Accounting Review` with expected universe, accounting table, unaccounted units, false completion path, correction, and verification.

Use `FINDING` for a demonstrated false completion path; `CLEAN` requires reconciling the independently established expected universe for the inspected operation. Use `LEAVE ALONE` for correctly limited best-effort output. If the reviewer cannot establish required membership or accounting, return `INSUFFICIENT EVIDENCE`, even when observed failures are zero.
