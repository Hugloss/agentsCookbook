---
name: state-authority-review
description: Finds competing representations that act as truth for the same logical state across persistence, caches, runtime, or UI.
license: MIT
---

# State Authority Review

Standalone, read-only state/source-of-truth review.

## INVARIANT

> **One logical state should have one authority; every other representation needs an explicit non-authoritative role.**

## HUNT

Inventory important representations across database, cache, memory, queue state, filesystem markers, receipts, snapshots, frontend stores, local/session storage, and derived status. Classify each as canonical, cache, replica, snapshot, draft, receipt, derived view, execution-local state, or mirror.

## PROVE

Trace readers, writers, refreshers, invalidators, and identity. Prove when two representations can independently override or reinterpret the same truth, especially persisted state versus inferred state.

## DO NOT REPORT

Do not report explicit caches, immutable receipts, editable drafts, snapshots, or derived presentation state merely because they duplicate data.

## PREFER

Keep one canonical authority and make other roles explicit. Delete synchronization code, fallback precedence, and mirror writes that exist only because authority is duplicated.

## OUTPUT

Return `# State Authority Review` with authority map, competing representations, real conflict paths, canonical state, removable mirrors/synchronization, and verification.
