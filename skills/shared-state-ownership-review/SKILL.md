---
name: shared-state-ownership-review
description: Finds race or synchronization reasoning that treats fresh/local mutable state as shared, or shared mutable state as ownerless.
license: MIT
---

# Shared State Ownership Review

Standalone, read-only concurrency state-ownership review.

## INVARIANT

> **A concurrency race or synchronization requirement exists only when mutable state is actually shared across concurrent owners.**

## HUNT

Hunt for:
- fresh copies of global/config/environment mappings treated as shared state;
- function-local containers mistaken for durable shared owners;
- aliases that hide genuinely shared mutable state;
- shared state mutated without a clear synchronization owner;
- locks or transactions guarding values that cannot cross concurrent ownership boundaries.

## PROVE

Trace allocation, aliasing, escape, lifetime, and concurrent access. Prove whether two concurrent owners can reach the same mutable object or durable representation. A shallow copy can retain shared children; process-local handles can still name the same file, row, service, or external resource.

Before recommending removal of a lock/transaction, inspect its entire protected operation and callers. A local mapping does not make another protected effect local. For a missing guard, establish conflicting reachable accesses and their consequence; shared mutation alone does not prove a race if another owner serializes it.

## DO NOT REPORT

Do not infer sharing merely from a value's origin, name, or similarity. Read-only shared state is not a mutation race by itself.

## PREFER

Name the mutable-state owner explicitly. Remove unnecessary synchronization for fresh/local copies and centralize synchronization where sharing is real.

## OUTPUT

Return `# Shared State Ownership Review` with the inspected allocation/access scope, alias trace, concurrent owners, sharing or false-sharing proof, synchronization consequence, correction, and verification.

Use `FINDING` only for a demonstrated ownership/synchronization error. `CLEAN` requires the relevant allocation, escapes, aliases, and protected accesses in the declared scope to be traced; `LEAVE ALONE` requires a positive local-state or existing-synchronization proof. Preserve an unavailable alias, caller, or external owner as `INSUFFICIENT EVIDENCE` when it prevents either conclusion.
