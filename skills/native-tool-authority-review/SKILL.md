---
name: native-tool-authority-review
description: Finds repository layers that reimplement semantics already owned by a native tool instead of delegating directly.
license: MIT
---

# Native Tool Authority Review

Standalone, read-only review of repository layers around native or external tools.

## INVARIANT

> **When a native tool already owns an operation's semantics, repository code may orchestrate that operation but must not create a second semantic implementation around it.**

## HUNT

Trace real operations that invoke package managers, build tools, container engines, cluster clients, VCS, process managers, test/lint/typecheck tools, infrastructure CLIs, or similar native authorities.

Hunt for repository layers that:
- reimplement resolution, installation, cache, retry, rollout, lifecycle, health, version-selection, scheduling, or state semantics already owned by the native tool;
- replace one native failure with a different command or fallback that claims to prove the same semantic fact;
- mirror native state into a second writable authority and reconcile the two;
- parse or normalize native configuration into a repository-owned semantic model without an independent repository policy need;
- add forwarding wrappers, compatibility shims, helper chains, or adapters whose only purpose is to make the native command fit local architecture;
- infer a native fact from adjacent evidence instead of observing the native authority that owns the fact.

Typical subjects include uv/pip/npm, Docker/BuildKit, Kubernetes/kubectl/Helm, Git, systemd/OS process facilities, pytest, Ruff, mypy, Terraform, and other repository-invoked CLIs.

## PROVE

For each finding show:
- the **native owner** and exact operation it already owns;
- the **repository path/call chain** that duplicates or substitutes those semantics;
- the duplicated semantic decision, state, retry/cache/lifecycle rule, or fallback proof;
- at least one real caller or workflow affected;
- why the repository layer is not enforcing a distinct trust, isolation, policy, protocol, credential, evidence, or product boundary;
- the smaller target path that delegates directly to the native tool while preserving the legitimate repository-owned boundary.

A thin wrapper is not a defect by itself. The finding requires proof that it owns or recreates native semantics rather than merely transporting an invocation through a meaningful boundary.

## DO NOT REPORT

Do not report a boundary merely because it wraps a native command when it genuinely owns:
- cwd, environment, workspace, sandbox, credential, or isolation binding;
- timeout, cancellation, process-tree containment, or resource limits that belong to the host/orchestrator;
- already-resolved input selection or authority transport without re-resolution;
- repository-specific security, publication, portability, or policy checks the native tool does not own;
- exact command/output/exit-status capture, provenance, receipt binding, or PASS/FAIL/INCOMPLETE projection;
- explicit operator-approved host preparation required for a repository-owned execution guarantee;
- a stable public protocol or substitution boundary with more than forwarding semantics.

Do not demand removal when the native tool cannot express the repository-specific invariant. Do not report from grep matches alone; trace the real operation.

## PREFER

Prefer the shortest authority path:

```text
caller
  -> required repository boundary
  -> native tool
  -> evidence/reporting
```

Delete shadow resolvers, custom package caches, duplicate retry engines, synthetic rollout/lifecycle models, compatibility shims, and pass-through helper chains when the native tool already owns those semantics.

If a wrapper is justified, make the guarantee it adds explicit and keep native semantics opaque rather than reconstructing them.

## OUTPUT

Return `# Native Tool Authority Review` with:
- inspected native operations and repository call paths;
- native owner and repository-owned guarantee per boundary;
- proven shadow-authority findings;
- justified wrappers/boundaries to leave alone;
- direct target path and deletion candidates;
- validation needed to prove behavior was preserved.

End with one:
- `CLEAN` — no shadow native-tool semantics were found in the completed inspection scope;
- `LEAVE ALONE` — suspicious wrappers were inspected and each adds a distinct justified repository boundary;
- `INSUFFICIENT EVIDENCE` — the native operation or repository call path could not be traced far enough to distinguish orchestration from semantic duplication.
