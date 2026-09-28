---
name: architecture-risk-triage
description: Routes evidence-backed architecture hotspots to the narrow specialist review that can prove the actual failure class.
license: MIT
---

# Architecture Risk Triage

Standalone, read-only discovery/router skill. It identifies where to aim deeper review; it is not a generic architecture rewrite.

## INVARIANT

> **Do not perform a vague architecture review when a sharper specialist can prove the problem, and do not infer repository-wide safety from an incomplete triage surface.**

## HUNT

Trace important production paths and hunt strong signals:
- stale async completion or UI work outliving its owner;
- partial multi-effect commit;
- retry/redelivery repeating a one-shot effect;
- leaked, prematurely closed, or ambiguously owned resources;
- inconsistent failure meaning, retryability, or recovery;
- repeated semantic decisions;
- one semantic truth whose authoritative owner changes by caller, outer workflow, entrypoint, lifecycle phase, or independent producer;
- multiple durable commit paths;
- resolved facts reconstructed from raw inputs;
- competing state authorities;
- invalid state combinations;
- named/legacy identities, exception sets, compatibility aliases, or fallback recognition that grant behavior not justified by a current semantic owner/consumer;
- repair, recovery, evidence, or debugging mechanisms that stage their own patches, archives, reports, temporary outputs, or OS/editor metadata inside the subject repository so incidental placement changes canonical source membership, packaging, or qualification;
- repeated observation;
- pass-through call chains;
- obsolete alternate paths;
- hidden side effects;
- oversized dependency surfaces;
- repository wrappers that recreate resolution, cache, retry, lifecycle, rollout, host configuration, package-manager ownership/certification, or other semantics already owned by a native/external tool;
- preflights that parse native-tool receipts, metadata, filesystem layout, or support tables to certify a state or operation the native tool itself already validates;
- native-tool workflows that ask operators to reselect model, provider, profile, endpoint, authentication mode, or equivalent host-owned settings even though usable native host configuration already exists;
- native/project workflows that redundantly redeclare or independently resolve ordinary executables already implied by platform or repository authority;
- hard admission, certification, release, readiness, or qualification gates driven by source shape, line counts, complexity, debt, formatting, source positions, or other heuristic proxies that do not directly prove the claimed semantic contract;
- slow, complex, nondeterministic, or implementation-coupled tests.

## PROVE

For each hotspot provide production responsibility, concrete evidence, risk class, and the specialist skill that fits. Prefer three proven hotspots over ten speculative ones.

Record the triage boundary: the production/test paths actually inspected and any material path left uninspected, unavailable, or truncated.

## DO NOT REPORT

Do not deeply solve every category. Do not rank files by size or complexity aesthetics. Do not create findings merely to fill a quota. Do not report "no architecture risk" when only a bounded triage surface was inspected.

## PREFER

Route each hotspot to the narrowest skill. Route path-dependent or producer-dependent ownership of one semantic truth to `single-source-of-truth-review`; route repeated interpretation inside one authority chain to `semantic-redecision-review`; route named/legacy identities, exception sets, compatibility residue, fallback recognition, or repair/transport self-contamination that changes source authority by incidental staging location to `hidden-authority-cucumber-attack`; route competing state representations to `state-authority-review`; route shadow native/external-tool semantics, redundant executable authority, and unnecessary re-decisions of usable native host configuration to `native-tool-authority-review`; route heuristic/source-shape checks promoted into hard qualification authority to `proxy-gate-authority-review`; use `call-chain-collapse-review` only when the defect is no-value indirection rather than split authority. Protect coherent owners. A clean result is only a statement about the completed triage boundary, not proof that the entire repository has no architecture risk.

## OUTPUT

Return `# Architecture Risk Triage` with:
- inspection boundary;
- evidence-backed hotspots and exact specialist routing;
- uninspected or unavailable paths;
- `No routed hotspots in inspected scope` when the bounded triage completed cleanly.

If the requested triage scope could not be completed, return `INSUFFICIENT EVIDENCE` rather than a clean absence claim.
