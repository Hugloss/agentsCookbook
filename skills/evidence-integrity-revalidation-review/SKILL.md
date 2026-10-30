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

Construct or trace a reachable content mutation that preserves the claimed identity, then follow a consumer that derives authority without verifying the binding. Account for existing signature/content verification, immutable storage guarantees, and the interval between validation and use; do not assume bytes can change where the actual owner prevents it. A digest stored beside mutable content is not by itself such a guarantee.

## DO NOT REPORT

Do not report a value whose current content/identity binding is already verified by a trusted owner and cannot change before this use, including a proven immutable storage or transport boundary. Serialization alone does not require redundant hashing; a self-asserted immutability flag or unchecked storage key is not proof.

## PREFER

Verify canonical identity where evidence crosses an untrusted or mutable boundary, reject mismatches before interpretation, and carry verified immutable ownership through subsequent uses. Recompute when that ownership no longer proves the binding; keep one canonical identity owner.

## OUTPUT

Return `# Evidence Integrity Revalidation Review` with artifact, claimed identity, tamper path, unchecked consumer, consequence, canonical verification boundary, and regression.

Use `FINDING` for reachable unchecked identity reuse, or `LEAVE ALONE` for a proven immutable verified value. `CLEAN` requires tracing relevant trust/mutation boundaries; unknown verification ownership or mutability is `INSUFFICIENT EVIDENCE`.
