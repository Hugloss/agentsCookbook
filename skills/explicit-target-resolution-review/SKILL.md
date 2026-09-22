---
name: explicit-target-resolution-review
description: Finds uniquely resolved explicit paths or symbols displaced by weaker inferred candidates, without confusing target intent with ownership proof.
license: MIT
---

# Explicit Target Resolution Review

Standalone, read-only target-selection review.

## INVARIANT

> **A uniquely resolved explicit target cannot be displaced by weaker inferred evidence, and explicit intent alone does not create stronger ownership authority.**

## HUNT

Hunt for:
- literal paths or qualified symbols replaced by structural/import/retrieval candidates;
- module-qualified names compared only to bare symbol names;
- explicit edit targets lost when dependencies or related symbols appear nearby;
- request wording order changing which explicit target survives;
- explicit test-edit intent being laundered into repository ownership.

## PROVE

Show the explicit target, the exact repository evidence that resolves it, the weaker evidence that displaces or reclassifies it, and the resulting wrong selection or authority state. Also verify true duplicate/multi-target ambiguity remains unresolved.

## DO NOT REPORT

Do not treat an explicit request as proof of semantic ownership. When the defect is specifically authority gained without proof, use `authority-escalation-review`.

## PREFER

Resolve strong explicit identifiers first, preserve them as target evidence, keep dependencies/related evidence separate, and require independent proof for ownership authority.

## OUTPUT

Return `# Explicit Target Resolution Review` with explicit target, resolution evidence, displacement path, authority distinction, correction, and verification.
