---
name: failure-contract-review
description: Finds failures whose meaning, propagation, retryability, or recovery contract changes across callers and layers.
license: MIT
---

# Failure Contract Review

Standalone, read-only failure semantics review.

## INVARIANT

> **A failure should have one explicit meaning and one predictable propagation or recovery contract.**

## HUNT

Hunt for:
- exception → `None` / false / empty-result conversion;
- catch-all log-and-continue behavior;
- retryable vs terminal meaning inferred differently by callers;
- the same failure represented as exception, status, sentinel, and log text;
- fallback that silently hides failure;
- recovery paths that reinterpret why an operation failed;
- cleanup code deciding business failure semantics.

## PROVE

Trace one real failure from origin to caller-visible outcome. Show where its meaning changes, becomes ambiguous, or forces downstream callers to guess retryability, absence, corruption, or terminal failure.

## DO NOT REPORT

Do not report a boundary that deliberately maps one stable internal failure into one stable public protocol result while preserving meaning. General repeated policy decisions belong to `semantic-redecision-review` unless the disputed fact is specifically failure semantics.

## PREFER

Keep one explicit failure/result contract at the existing semantic owner and map it once at true protocol boundaries. Delete fallback branches, sentinel translation, and caller-side failure reconstruction that become unnecessary.

## OUTPUT

Return `# Failure Contract Review` with findings: originating failure, current representations, semantic divergence, real consequence, canonical contract, mappings/branches that can disappear, verification.
