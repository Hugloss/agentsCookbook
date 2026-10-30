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

For one logical state, scope and generation, trace readers, writers, refreshers, invalidators and the rule that accepts a representation as truth. Show a reachable conflict where two representations can independently override or reinterpret that same state, and the material consequence. Establish the actual consistency/merge contract before interpreting delayed propagation as conflicting authority.

## DO NOT REPORT

Do not report explicit caches, immutable receipts, editable drafts, snapshots or derived presentation state merely because they duplicate data. Replicas or concurrent writers governed by one declared consensus/merge contract do not require one physical process. Distinct generations and independently owned facts are not competing representations of the same state.

## PREFER

Keep one canonical authority and make other roles explicit. Delete synchronization code, fallback precedence, and mirror writes that exist only because authority is duplicated.

## OUTPUT

Return `# State Authority Review` with state/scope/generation, authority and consistency rules, inspected read/write paths, proved conflict, canonical state, justified mirrors and focused verification.

Use `FINDING` for a reachable competing-truth path; `CLEAN` only when the declared state's accepting readers and writers were traced with no competing authority or unresolved material consistency rule; `LEAVE ALONE` for proved non-authoritative or coherently merged representations; or `INSUFFICIENT EVIDENCE` when acceptance or consistency rules remain unresolved.
