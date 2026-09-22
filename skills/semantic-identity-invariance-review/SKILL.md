---
name: semantic-identity-invariance-review
description: Finds authoritative identities that change on semantic no-ops or stay unchanged across semantic changes they claim to cover.
license: MIT
---

# Semantic Identity Invariance Review

Standalone, read-only identity semantics review.

## INVARIANT

> **An authoritative identity changes exactly when the semantics it claims to identify change.**

## HUNT

Hunt for identity inputs polluted by:
- unordered collection iteration or caller order;
- presentation rank, display roles, diagnostics, timing, or pagination metadata;
- equivalent path, packaging, newline, or serialization representations;
- cache warmth or persistence layout;
- omitted semantic fields that allow materially different objects to collide.

## PROVE

Construct a metamorphic pair. First change only representation or presentation and prove the semantic object is unchanged; the authoritative identity must remain equal. Then change one covered semantic fact; the identity must change.

Trace the exact fields admitted into the identity and the semantic contract they are supposed to represent.

## DO NOT REPORT

Do not report order changes when order is itself semantic. Do not report a deliberately presentation-scoped identity for changing with presentation when no stronger authority is inferred from it.

## PREFER

Define one canonical semantic projection, exclude diagnostics and bounded presentation, normalize equivalent representations, and hash that projection once.

## OUTPUT

Return `# Semantic Identity Invariance Review` with findings: identity owner, claimed semantics, no-op mutation, semantic mutation, observed identity behavior, consequence, canonical identity inputs, verification.
