---
name: evidence-projection-preservation-review
description: Finds projections that silently erase, replace, or hide admitted evidence instead of preserving it or accounting for its exclusion.
license: MIT
---

# Evidence Projection Preservation Review

Standalone, read-only evidence-flow review.

## INVARIANT

> **Every admitted source fact must survive a projection or have an explicit, inspectable exclusion reason.**

## HUNT

Hunt across model, API, compact, CLI, MCP, report, and UI projections for:
- map/filter stages that drop source rows silently;
- candidates or changed paths disappearing because they are non-actionable;
- missing, excluded, malformed, denied, stale, or unresolved evidence omitted from output;
- one evidence class replacing another instead of coexisting;
- compact views that become de facto authority despite losing material facts.

## PROVE

Trace one admitted source fact from its producer through each projection. Show the exact stage where it disappears, is overwritten, or loses its status/provenance, and demonstrate a downstream consumer that can no longer distinguish absence from exclusion.

## DO NOT REPORT

Do not report a deliberately lossy presentation that clearly declares its scope and is never used as complete or authoritative evidence.

## PREFER

Preserve canonical evidence and project views from it. Carry explicit omission, truncation, exclusion, or unresolved state instead of encoding those states as absence.

## OUTPUT

Return `# Evidence Projection Preservation Review` with findings: source fact, projection path, loss point, downstream ambiguity, explicit accounting required, minimal correction, verification.
