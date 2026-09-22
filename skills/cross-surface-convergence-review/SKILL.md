---
name: cross-surface-convergence-review
description: Finds the same semantic fact or authority result diverging across API, CLI, MCP, compact, report, or persistence surfaces.
license: MIT
---

# Cross-Surface Convergence Review

Standalone, read-only public-surface consistency review.

## INVARIANT

> **Equivalent public surfaces must expose the same semantic fact and authority state from the same canonical evidence.**

## HUNT

Hunt across API, CLI, MCP, compact, report, UI, serialized, and persisted projections for:
- one surface resolving while another remains ambiguous;
- candidate vs authority status changing by adapter;
- freshness, completeness, provenance, or visibility disappearing on one surface;
- adapter-local reranking or reinterpretation;
- duplicated semantic logic that drifts between surfaces.

## PROVE

Run or trace the same semantic request through at least two surfaces from the same source/generation. Normalize presentation-only differences and compare the resulting semantic and authority state. Identify the adapter or projection where divergence appears.

## DO NOT REPORT

Do not report intentional formatting, naming, transport, or bounded-presentation differences that preserve the same semantic state and authority.

## PREFER

Keep one canonical semantic owner and make public surfaces thin projections over it. Compare surfaces through a shared semantic projection in regression tests.

## OUTPUT

Return `# Cross-Surface Convergence Review` with surfaces compared, canonical evidence, divergent fields, authority consequence, duplicated logic to remove, verification.
