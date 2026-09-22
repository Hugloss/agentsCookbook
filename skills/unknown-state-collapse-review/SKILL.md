---
name: unknown-state-collapse-review
description: Finds unknown, missing, incomplete, stale, or invalid states silently collapsed into zero, false, empty, absent, or success.
license: MIT
---

# Unknown State Collapse Review

Standalone, read-only uncertainty semantics review.

## INVARIANT

> **Unknown, missing, incomplete, stale, and invalid are distinct states until an explicit contract proves they may be collapsed.**

## HUNT

Hunt for:
- missing metrics defaulted to zero;
- unknown booleans coerced to false;
- missing evidence represented as empty evidence;
- stale or invalid receipts treated as current absence;
- incomplete scans returned as no findings;
- default values that erase whether a fact was observed;
- serializers that omit uncertainty and readers that reconstruct certainty.

## PROVE

Trace the richer source state into the collapsed representation, then show a downstream branch that behaves differently for genuine zero/false/empty/success than it should for unknown or invalid.

## DO NOT REPORT

When the disputed distinction is specifically exception/failure meaning or retryability, use `failure-contract-review`. Do not report an explicit domain contract that intentionally equates the states.

## PREFER

Use explicit tagged states or separate value/status fields. Preserve uncertainty through serialization and projections.

## OUTPUT

Return `# Unknown State Collapse Review` with source states, collapse point, downstream semantic error, canonical representation, correction, verification.
