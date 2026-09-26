---
name: entrypoint-authority-review
description: Finds one conceptual operator action whose launch defaults or configuration semantics are independently owned by multiple entrypoints.
license: MIT
---

# Entrypoint Authority Review

Standalone, read-only review of operator and automation entrypoints.

## INVARIANT

> **One conceptual action may have multiple convenient entrypoints, but its launch semantics and defaults must have one owner.**

## HUNT

Trace real ways humans, agents, CI, Make targets, package scripts, task runners, shell scripts, Python modules, console commands, and hosted environments start the same conceptual action.

Hunt for:
- two or more entrypoints that independently encode the same defaults, budgets, paths, modes, environment, tool selection, output location, or execution policy;
- copied command lines whose flags must be kept manually synchronized;
- local, CI, and hosted launch paths that claim to run the same action but resolve configuration separately;
- a convenience wrapper that becomes a second configuration owner instead of selecting and transporting one resolved profile;
- documentation that requires operators or agents to remember which invocation carries the authoritative settings;
- obsolete launch paths left beside a canonical entrypoint after convergence.

Multiple syntactic entrypoints are not themselves a defect. The defect is competing ownership of launch semantics.

## PROVE

For each finding show:
- the **conceptual action** the entrypoints claim to launch;
- each real entrypoint and at least one caller/operator workflow using it;
- the duplicated launch facts each path owns;
- whether those facts can drift independently;
- the intended single semantic/configuration owner;
- the target shape where alternate entrypoints are thin selectors or transports into that owner;
- any obsolete entrypoint that can be removed rather than preserved.

A useful target often looks like:

```text
operator / agent / CI
  -> thin entrypoint alias
  -> one stored profile or configuration owner
  -> one execution owner
  -> one result/evidence contract
```

## DO NOT REPORT

Do not report:
- `make benchmark` and `uv run ...` merely because both exist when they select the same stored profile and execution owner;
- platform-specific launch syntax that transports the same resolved settings without re-deciding them;
- a stable public CLI plus an internal API when they intentionally serve different contracts;
- CI adding CI-owned timeout, credential, sandbox, artifact-upload, or isolation policy around the same underlying action;
- separate commands that perform genuinely different conceptual actions;
- a wrapper solely because it is thin; use `call-chain-collapse-review` when the problem is no-value indirection rather than competing launch ownership.

## PREFER

Prefer one obvious normal command per common environment, backed by one configuration owner.

For example:

```text
make benchmark
uv run ... benchmark
        \ /
         v
 checked-in benchmark profile
         |
 existing benchmark implementation
```

Keep environment-specific entrypoints boring: select a profile, bind necessary host constraints, invoke the existing owner. Do not mirror its defaults.

Prefer deletion of stale alternate launch paths over compatibility shims when callers are controlled.

## OVERLAP

- Use `call-chain-collapse-review` when the defect is forwarding hops with no guarantee.
- Use `native-tool-authority-review` when repository code recreates semantics owned by an external/native tool.
- Use `cross-surface-convergence-review` when equivalent surfaces already exist but produce different semantic results or authority.
- Use `state-authority-review` when competing representations, rather than launch paths, act as truth.
- Use this skill when the specific question is **who owns how one conceptual action is launched and configured**.

## OUTPUT

Return `# Entrypoint Authority Review` with:
- conceptual action and inspected entrypoints;
- launch/configuration owner for each path;
- proven duplicate-owner findings;
- justified aliases or environment-specific boundaries to leave alone;
- canonical target entrypoint(s) and single semantic/configuration owner;
- deletion/convergence candidates;
- validation needed to prove all supported entrypoints resolve equivalently.

End with one:
- `CLEAN` — supported entrypoints converge on one launch/configuration owner;
- `LEAVE ALONE` — multiple entrypoints are justified aliases or distinct contracts and do not duplicate launch authority;
- `INSUFFICIENT EVIDENCE` — callers or launch/configuration ownership could not be traced far enough to prove convergence or duplication.
