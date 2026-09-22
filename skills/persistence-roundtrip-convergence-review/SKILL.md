---
name: persistence-roundtrip-convergence-review
description: Finds persisted state whose save/reopen/decode path changes semantics or identity instead of converging exactly or failing explicitly.
license: MIT
---

# Persistence Roundtrip Convergence Review

Standalone, read-only persistence semantics review.

## INVARIANT

> **Persist → reopen → decode must preserve the same semantic state and identity, or fail explicitly.**

## HUNT

Hunt in databases, CAS, files, snapshots, journals, and codecs for:
- lossy type coercion or overflow handling;
- non-canonical encodings;
- absent/default fields changing meaning after reopen;
- order-dependent reconstruction;
- path, mode, newline, or platform representation drift;
- corrupted persisted bytes being accepted as valid state;
- warm/reopened behavior differing from the equivalent cold semantic state.

## PROVE

Create or trace an exact roundtrip from authoritative in-memory state to persisted representation and back. Compare semantic state and identity before/after, then test malformed or non-canonical persisted data.

## DO NOT REPORT

Do not report harmless storage-layout changes that decode to the same semantic object and are not themselves public identity.

## PREFER

Use canonical codecs, explicit schema/version handling, integrity checks, and fail-closed decoding.

## OUTPUT

Return `# Persistence Roundtrip Convergence Review` with persisted owner, roundtrip path, semantic drift or invalid acceptance, consequence, canonical representation, verification.
