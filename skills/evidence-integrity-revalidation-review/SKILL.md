---
name: evidence-integrity-revalidation-review
description: Finds reusable evidence whose claimed content identity is trusted without recomputing or verifying it before reuse, comparison, or delta.
license: MIT
---

# Evidence Integrity Revalidation Review

Standalone, read-only evidence-integrity review.

## INVARIANT

> **A reusable evidence identity is trustworthy only after the consumer verifies that the current content still matches that identity.**

## HUNT

Hunt for:
- previous/current packets compared without rehashing;
- receipts, snapshots, manifests, or deltas that trust a stored digest field;
- nested content changed while a top-level identity is retained;
- identity-bearing fields excluded from verification accidentally;
- mutation after validation but before reuse;
- foreign or malformed identities accepted as if valid.

## PROVE

Modify evidence content while preserving its claimed identity, then trace a consumer that accepts, compares, or derives authority from the tampered artifact without recomputing the canonical identity.

## DO NOT REPORT

Do not report immutable in-process values that cannot be altered between identity creation and use and are never serialized, transported, cached, or supplied externally.

## PREFER

Recompute canonical identity at every trust/reuse boundary, reject mismatches before interpretation, and keep one canonical identity owner.

## OUTPUT

Return `# Evidence Integrity Revalidation Review` with artifact, claimed identity, tamper path, unchecked consumer, consequence, canonical verification boundary, and regression.
