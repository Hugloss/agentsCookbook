---
name: evidence-visibility-enforcement-review
description: Finds denied, hidden, or out-of-scope evidence that leaks into selection, projection, authority, diagnostics, or public output.
license: MIT
---

# Evidence Visibility Enforcement Review

Standalone, read-only evidence-visibility boundary review.

## INVARIANT

> **Evidence excluded by visibility or admission policy must not influence or appear beyond that boundary.**

## HUNT

Hunt for denied/hidden/out-of-scope rows entering:
- retrieval or ranking;
- candidate selection;
- ownership/authority proof;
- related-evidence projections;
- diagnostics or compact reports;
- cache keys/results that cross visibility scopes.

## PROVE

Trace one denied or hidden evidence item from policy evaluation to a downstream surface. Show either direct exposure or a changed decision caused by the excluded evidence.

## DO NOT REPORT

Do not report evidence intentionally available in a privileged surface whose caller is explicitly authorized for that visibility scope.

## PREFER

Apply visibility filtering once at the earliest canonical evidence boundary, bind visibility scope into reusable caches, and prevent downstream layers from reconstructing excluded data.

## OUTPUT

Return `# Evidence Visibility Enforcement Review` with visibility rule, leaked evidence path, affected surface/decision, consequence, earliest enforcement boundary, verification.
