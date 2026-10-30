---
name: roundtrip-capacity-contract-review
description: Finds valid outputs or requests that cannot traverse documented downstream or round-trip paths because layer bounds are incompatible.
license: MIT
---

# Roundtrip Capacity Contract Review

Standalone, read-only bounded-interface review.

## INVARIANT

> **If one layer declares a payload valid and reusable downstream, every required downstream or round-trip boundary must accept that valid payload or expose an explicit transformation contract.**

## HUNT

Hunt for:
- core payload limits larger than transport/API limits;
- legal responses too large to be supplied back as previous/input state;
- nested layers with silently stricter byte, item, depth, or field bounds;
- dense projections that pass local validation but exceed the next supported boundary;
- bounds duplicated independently across adapters;
- truncation introduced only after an upstream layer has already promised completeness.

## PROVE

Construct or derive a boundary payload valid under the producer/core contract, then trace it through the required documented consumer or round-trip path. Account for actual units and representation changes: characters versus encoded bytes, escaping/framing, decompression, item count, and nesting depth where applicable. One reachable valid counterexample proves a mismatch; do not require materializing a dangerous maximum-size payload. Show the exact boundary that rejects or cannot represent it.

## DO NOT REPORT

Do not report intentionally different bounds when the contract explicitly requires a lossy transform and authority/completeness semantics account for that transform.

## PREFER

Own one effective bound at the semantic layer and reuse it through transports. Where a transform is necessary, make it explicit, deterministic, and authority-aware.

## OUTPUT

Return `# Roundtrip Capacity Contract Review` with producer bound, downstream bounds, failing valid payload, broken composition path, correction, and verification.

Use `FINDING` for a valid payload that provably fails a required boundary. `CLEAN` requires checking the named supported composition paths and limit units; unknown downstream limits or transformation semantics require `INSUFFICIENT EVIDENCE`.
