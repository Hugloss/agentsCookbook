---
name: single-owner-contract-review
description: Finds one repository contract being independently synthesized or patched in multiple layers instead of owned once.
license: MIT
---

# Single Owner Contract Review

Standalone, read-only review of repository-owned facts, prerequisites, generated artifacts, and materialization contracts.

## INVARIANT

> **A repository-owned fact or prerequisite should be established by one semantic owner at the phase where it becomes required. Other layers may transport, validate, project, or fail closed on that fact, but should not independently synthesize compensating copies, placeholders, defaults, or repair steps just to keep adjacent paths working.**

## HUNT

Trace one real build, bootstrap, packaging, release, runtime, persistence, or test path end to end. Hunt for the same contract or prerequisite being independently recreated in several places, including:
- `mkdir`, `touch`, copy, default, normalize, inject, generate, ensure, repair, or "if missing, create" logic for the same path or fact;
- bootstrap/Make targets, source normalization, build hooks, packaging code, CI, runtime startup, and tests each making the same prerequisite appear;
- placeholder files or directories created only because another layer assumes they exist;
- source-tree preparation and package/archive preparation both synthesizing the same artifact without one declared producer;
- multiple helpers that each reconstruct the same derived file, manifest, status, identity, or configuration fragment;
- downstream layers compensating for an upstream contract that is absent, ambiguous, or attached to the wrong lifecycle phase.

The signal is not repeated syntax. The signal is several independently reachable mechanisms trying to make the **same semantic contract** true.

## PROVE

Before reporting a finding:
1. Name the exact contract or fact being established.
2. Trace at least one real workflow that depends on it.
3. Enumerate the reachable touch points and classify each as **owner**, **transport**, **validation**, **projection**, or **compensation**.
4. Prove that at least two touch points independently synthesize, repair, default, or recreate the same contract rather than merely consume or verify it.
5. Identify the lifecycle phase where the fact actually becomes required and the smallest coherent owner for that phase.
6. Show a concrete consequence of split ownership: one path fails when a compensator is absent, two paths can drift, unrelated paths must fabricate the fact, or changes require synchronized repair logic.
7. State which compensating mechanisms can disappear once the owner contract is corrected.

A finding is strongest when removing one compensator exposes another hidden dependency. That demonstrates a split contract rather than harmless repeated setup.

## DO NOT REPORT

Do not report:
- repeated syntax that establishes different local facts;
- consumer-side validation of an owner-produced fact;
- trust-boundary validation, checksum verification, or fail-closed checks;
- transport or projection into another representation when no second semantic owner is created;
- per-workspace temporary/cache directory creation whose lifecycle is intentionally local;
- test fixtures that create isolated test-owned inputs rather than production prerequisites;
- release/package staging that intentionally creates a release artifact from source inputs when editable/source execution does not require that artifact;
- two mechanisms that look similar but operate at genuinely different lifecycle phases with different contracts.

Do not collapse legitimate producer/consumer boundaries merely to reduce file count. Do not report from grep matches alone.

If the repeated behavior is the same **policy decision** being interpreted more than once, use `semantic-redecision-review`. If repository code is recreating semantics already owned by uv, npm, Git, Docker, Kubernetes, or another external/native tool, use `native-tool-authority-review`.

## PREFER

Prefer one explicit owner and a short contract path:

```text
source inputs
  -> semantic/materialization owner
  -> explicit artifact or resolved fact
  -> transport / validation / projection
  -> consumer
```

Move creation to the phase that truly owns it. Remove placeholder fabrication from unrelated phases. Let consumers either consume the owner-produced value or fail closed with a clear missing-contract error.

When a release artifact is not a source prerequisite, keep it out of editable/bootstrap/source-normalization paths and create it only at the release/package boundary that owns it.

## OUTPUT

Return `# Single Owner Contract Review` with:
- contract/fact under review;
- real workflow traced;
- touch-point table with owner/transport/validation/projection/compensation classification;
- proven split-owner findings;
- correct lifecycle owner and target contract;
- compensating mechanisms that can be deleted;
- focused regression needed to prevent recurrence;
- inspected scope and any untraced paths.

End with one:
- `CLEAN` — no split contract ownership was proven in the completed inspection scope;
- `LEAVE ALONE` — repeated touches were traced and each is a distinct justified owner/consumer boundary;
- `INSUFFICIENT EVIDENCE` — the real workflow or lifecycle ownership could not be traced far enough to distinguish compensation from legitimate phase-local behavior.
