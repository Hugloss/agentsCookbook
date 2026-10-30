---
name: resource-lifetime-review
description: Finds resources that can leak, close too early, or outlive the explicit owner whose lifetime should govern them.
license: MIT
---

# Resource Lifetime Review

Standalone, read-only lifetime ownership review.

## INVARIANT

> **A resource must live exactly as long as its owning operation, scope, lease, or process requires.**

## HUNT

Hunt acquisition/use/release paths for:
- files and temp directories;
- locks and leases;
- database connections and transactions;
- sockets, streams, subscriptions, watchers;
- child processes and workers;
- timers and background tasks;
- borrowed handles passed across async boundaries.

## PROVE

Identify who acquires the resource, who owns its lifetime, every relevant path that can release or abandon it, and one realistic ordering that causes leak, premature release, or use-after-close. Naming ambiguity alone is a lead; establish its concrete lifetime consequence.

Include partial acquisition, failure before context/fixture entry completes, cancellation, ownership transfer, and escaped borrowers when reachable. Trace whether cleanup itself can fail or be cancelled and whether another owner finishes it. Cancellation of a task or closing one handle does not prove an external call, process, or shared resource stopped. A borrower must not destroy the owning service merely to release its own handle.

## DO NOT REPORT

Do not report intentionally process-lifetime resources with a clear process owner. UI render/view lifetime belongs to `ui-lifecycle-race-review` when the defect is specifically delayed work outliving a view generation.

## PREFER

Use lexical/structured ownership, existing context-management primitives, and one explicit cleanup owner. Delete defensive cleanup spread across unrelated callers once lifetime authority is clear.

## OUTPUT

Return `# Resource Lifetime Review` with the inspected acquisition/borrow/release scope and findings: resource, lifetime owner, release paths, harmful ordering, consequence, target ownership boundary, cleanup code that can disappear, and deterministic verification.

Use `FINDING` for a demonstrated lifetime violation. `CLEAN` requires the declared normal, partial-start, failure, and cancellation paths to have traced ownership; `LEAVE ALONE` requires a positive valid lifetime/transfer proof. Missing release or external-stop semantics remains `INSUFFICIENT EVIDENCE` if no violation is established. Report executed cleanup evidence separately from source reasoning.
