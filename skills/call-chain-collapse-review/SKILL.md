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

Show the real call chain and classify each hop. A useful hop should enforce a trust, transaction, isolation, protocol, domain-invariant, or meaningful substitution boundary.

## DO NOT REPORT

Do not report a meaningful thin boundary merely because it is thin. Do not optimize for fewer files.

## PREFER

Delete no-value hops and call the existing real owner more directly. Update callers rather than preserving compatibility wrappers for code you control.

## OUTPUT

Return `# Call Chain Collapse Review` with current chain, guarantee per hop, redundant hops, target chain, removed code/concepts, behavior-preservation proof.
