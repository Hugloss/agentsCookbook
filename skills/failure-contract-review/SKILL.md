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

Establish the applicable error/result contract, then trace one real failure from origin to caller-visible outcome and recovery decision. Show where its meaning changes, becomes ambiguous, or forces downstream callers to guess retryability, absence, corruption, or terminal failure, with a concrete wrong outcome.

Distinguish failure to observe an effect from proof that the effect did not happen. A timeout after remote success, cancellation during commit, or cleanup error after completion must not automatically become safe-to-retry absence or erase the original outcome. Inspect actual operation/client semantics instead of inferring retryability from an exception's name.

## DO NOT REPORT

Do not report a boundary that deliberately maps one stable internal failure into one stable public protocol result while preserving meaning. General repeated policy decisions belong to `semantic-redecision-review` unless the disputed fact is specifically failure semantics.

## PREFER

Keep one explicit failure/result contract at the existing semantic owner and map it once at true protocol boundaries. Delete fallback branches, sentinel translation, and caller-side failure reconstruction that become unnecessary.

## OUTPUT

Return `# Failure Contract Review` with the inspected failure/consumer scope and findings: originating failure, current representations, semantic divergence, real consequence, canonical contract, mappings/branches that can disappear, and verification.

Use `FINDING` for a proved meaning or recovery violation. `CLEAN` requires relevant origin, translation, caller, and recovery paths in the declared scope to preserve the established contract; `LEAVE ALONE` requires a positively justified protocol mapping. Missing governing semantics is `INSUFFICIENT EVIDENCE` when no defect is proved, not permission to invent a failure policy.
