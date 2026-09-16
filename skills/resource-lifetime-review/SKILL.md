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

Identify who acquires the resource, who owns its lifetime, every path that can release or abandon it, and one realistic ordering that causes leak, premature release, use-after-close, or ownership ambiguity.

## DO NOT REPORT

Do not report intentionally process-lifetime resources with a clear process owner. UI render/view lifetime belongs to `ui-lifecycle-race-review` when the defect is specifically delayed work outliving a view generation.

## PREFER

Use lexical/structured ownership, existing context-management primitives, and one explicit cleanup owner. Delete defensive cleanup spread across unrelated callers once lifetime authority is clear.

## OUTPUT

Return `# Resource Lifetime Review` with findings: resource, acquisition path, lifetime owner, release paths, harmful ordering, consequence, target ownership boundary, cleanup code that can disappear, deterministic verification.
