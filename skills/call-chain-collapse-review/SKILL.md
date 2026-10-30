---
name: call-chain-collapse-review
description: Finds forwarding layers and wrappers that lengthen real call paths without adding a meaningful guarantee.
license: MIT
---

# Call Chain Collapse Review

Standalone, read-only indirection review.

## INVARIANT

> **Every hop in a call chain must earn its existence.**

## HUNT

Trace real operations through components, hooks, helpers, services, facades, adapters, controllers, repositories, and domain owners. For each hop ask what guarantee it adds. Hunt for layers that only forward arguments, rename methods, relay callbacks, or duplicate error mapping.

## PROVE

Trace a real caller to the semantic owner and identify the contract each hop enforces. Before proposing deletion, inspect supported callers, registration/extension use, error/cancellation behavior and substitution needs. Show what avoidable forwarding or duplicated mapping disappears and why the direct path preserves those obligations. Treat unresolved dynamic callers as unknown, not unused.

## DO NOT REPORT

Do not report a meaningful thin boundary merely because it is thin. Preserve justified public compatibility, trust, transaction, isolation, protocol, lifecycle, observability and substitution boundaries. A function's length does not establish whether it owns one of these guarantees. Do not optimize for fewer files.

## PREFER

Delete no-value hops and call the existing real owner more directly. Update callers rather than preserving compatibility wrappers for code you control.

## OUTPUT

Return `# Call Chain Collapse Review` with inspected caller chain, guarantee per hop, proved redundant forwarding, direct target path, removed work/concepts and behavior-preservation evidence.

Use `FINDING` for a proved removable hop with its obligations preserved; `CLEAN` only for a fully traced declared chain whose hops have justified obligations; `LEAVE ALONE` for positively justified boundaries; or `INSUFFICIENT EVIDENCE` when caller or extension obligations remain unresolved. A deletion proposal is not proof that the changed path was executed.
