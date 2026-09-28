---
name: native-tool-authority-review
description: Finds repository layers that reimplement semantics already owned by a native tool instead of delegating directly.
license: MIT
---

# Native Tool Authority Review

Standalone, read-only review of repository layers around native or external tools.

## INVARIANT

> **When a native tool or already-established execution authority owns a decision, repository code may orchestrate and transport that decision but must not reimplement it, re-resolve it, or force callers to redeclare it.**

The correct path should be the shortest authority path. Ordinary tools implied by the selected platform, repository, or native workflow should work without repetitive declarations. Explicit authority is useful when it adds a genuinely new capability, choice, trust boundary, or policy requirement.

## HUNT

Trace real operations that invoke package managers, build tools, container engines, cluster clients, VCS, process managers, test/lint/typecheck tools, infrastructure CLIs, or similar native authorities.

For each process/tool launch, first identify who already owns choosing that executable:

- **platform authority** — runtime machinery intrinsic to the supported host/executor;
- **repository-native authority** — the repository has already selected the native workflow or package manager;
- **locked project environment** — a native tool resolves the package-local executable from the project's declared environment;
- **explicit exceptional capability** — the workload genuinely introduces a capability not implied by the established execution mode.

Hunt for repository layers that:
- ask the operator or agent to choose model, provider, profile, endpoint, authentication mode, executable, or equivalent native settings when a usable native or upstream authority already exists;
- require Goons, tasks, manifests, or callers to repeat obvious executable declarations already implied by platform or repository authority;
- independently locate or resolve a package-local executable already owned by a native environment command, such as resolving pytest separately from uv run pytest;
- copy native host configuration into repository profiles, trial manifests, benchmark flags, or prompts and then require the two authorities to stay synchronized;
- reimplement resolution, installation, cache, retry, rollout, lifecycle, health, version-selection, scheduling, or state semantics already owned by the native tool;
- replace one native failure with a different command or fallback that claims to prove the same semantic fact;
- mirror native state into a second writable authority and reconcile the two;
- parse or normalize native configuration into a repository-owned semantic model without an independent repository policy need;
- add forwarding wrappers, compatibility shims, helper chains, executable manifests, or adapters whose only purpose is to make the native command fit local architecture;
- infer a native fact from adjacent evidence instead of observing the native authority that owns the fact;
- choose an executable from ambient PATH even though an upstream authority already selected the tool or environment;
- hide a surprising new capability behind an otherwise ordinary native workflow without making the real boundary visible.

Typical subjects include uv/pip/npm/pnpm, Docker/BuildKit, Kubernetes/kubectl/Helm, Git, systemd/OS process facilities, pytest, Ruff, mypy, Terraform, and other repository-invoked CLIs.

The target is not a giant scanner for shell commands. Trace actual process-creation paths and authority ownership.

## PROVE

For each finding show:
- the real operation and process/tool launch path;
- the **native or upstream owner** that already establishes the executable or semantics;
- whether authority is platform-owned, repository-native, locked-project, or an explicit exceptional capability;
- the repository path/call chain that duplicates, re-resolves, substitutes, or unnecessarily redeclares that authority;
- the duplicated semantic decision, executable selection, state, retry/cache/lifecycle rule, or fallback proof;
- at least one real caller or workflow affected;
- why the repository layer is not enforcing a distinct trust, isolation, policy, protocol, credential, evidence, or product boundary;
- the smaller target path that transports the already-resolved authority or delegates directly to the native tool;
- for an allegedly hidden capability, why a normal caller could not reasonably infer it from the already-selected execution mode.

A thin wrapper is not a defect by itself. An explicit executable declaration is not a defect by itself. The finding requires proof that the layer recreates or restates authority without adding information, or that it introduces a genuinely new capability invisibly.

A strong proof often looks like:

~~~text
repository/native authority already selects tool
  -> caller redeclares same tool
  -> helper resolves it again
  -> execution
~~~

or:

~~~text
ordinary native workflow
  -> helper
  -> surprising new capability not implied upstream
~~~

## DO NOT REPORT

Do not ask the operator to choose how to honor native model/provider/profile settings merely because execution is isolated. Isolation may bind cwd, workspace, sandbox, environment, credentials, timeout, or evidence capture while the native tool continues to resolve its own host configuration.

Do not require explicit declarations for ordinary dependencies already established by:
- the supported execution platform;
- repository-native project authority;
- a locked/native environment that owns package-local executable resolution;
- an upstream resolved execution contract transported unchanged into the current layer.

For example, if repository authority already establishes a uv workflow, uv run pytest does not imply that the repository should separately resolve or globally declare Python and pytest. uv owns that native project-environment resolution.

Do not report a genuinely exceptional capability merely because it is explicit. A workload that newly requires kubectl, Terraform, Docker, browser automation, cloud credentials, or another non-obvious capability may legitimately make that boundary visible when no higher authority already implies it.

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

When the request says to use a native tool, default to the tool's existing host/project authority. Do not invent a repository-owned model/profile/executable choice and do not ask a preference question unless:
- the requested operation explicitly requires an override;
- no usable native/project authority exists;
- multiple native authorities are simultaneously applicable and the native layer cannot resolve them; or
- applying the existing authority would violate an explicit isolation, security, reproducibility, or workload contract.

Repository-owned workload policy remains repository-owned. For example, a benchmark may define its default corpus, lane set, repetition count, or paired-smoke profile while Codex still owns its model/provider configuration. These are different authorities and should not be collapsed.

Prefer the shortest authority path:

~~~text
caller
  -> required repository boundary
  -> already-selected native tool/environment
  -> evidence/reporting
~~~

For project-local commands prefer:

~~~text
repository authority
  -> native environment owner
  -> package-local executable
~~~

rather than separately resolving every executable.

Delete shadow resolvers, custom package caches, duplicate retry engines, synthetic rollout/lifecycle models, redundant executable declarations, compatibility shims, and pass-through helper chains when the existing authority already owns those semantics.

If a wrapper is justified, make the guarantee it adds explicit and keep native semantics opaque rather than reconstructing them.

## OUTPUT

Return # Native Tool Authority Review with:
- inspected native operations and real process/tool launch paths;
- authority class and owner per executable/tool decision;
- proven shadow-authority or redundant-redeclaration findings;
- genuinely exceptional capabilities that should remain explicit;
- justified wrappers/boundaries to leave alone;
- direct target path and deletion candidates;
- validation needed to prove behavior was preserved.

End with one:
- CLEAN — no shadow native-tool semantics or redundant authority redeclarations were found in the completed inspection scope;
- LEAVE ALONE — suspicious wrappers/declarations were inspected and each adds a distinct justified boundary or capability;
- INSUFFICIENT EVIDENCE — the native operation or process/tool authority path could not be traced far enough to distinguish orchestration from semantic duplication.
