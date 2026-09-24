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
- multiple durable commit paths;
- resolved facts reconstructed from raw inputs;
- competing state authorities;
- invalid state combinations;
- repeated observation;
- pass-through call chains;
- obsolete alternate paths;
- hidden side effects;
- oversized dependency surfaces;
- slow, complex, nondeterministic, or implementation-coupled tests.

## PROVE

For each hotspot provide production responsibility, concrete evidence, risk class, and the specialist skill that fits. Prefer three proven hotspots over ten speculative ones.

Record the triage boundary: the production/test paths actually inspected and any material path left uninspected, unavailable, or truncated.

## DO NOT REPORT

Do not deeply solve every category. Do not rank files by size or complexity aesthetics. Do not create findings merely to fill a quota. Do not report "no architecture risk" when only a bounded triage surface was inspected.

## PREFER

Route each hotspot to the narrowest skill. Protect coherent owners. A clean result is only a statement about the completed triage boundary, not proof that the entire repository has no architecture risk.

## OUTPUT

Return `# Architecture Risk Triage` with:
- inspection boundary;
- evidence-backed hotspots and exact specialist routing;
- uninspected or unavailable paths;
- `No routed hotspots in inspected scope` when the bounded triage completed cleanly.

If the requested triage scope could not be completed, return `INSUFFICIENT EVIDENCE` rather than a clean absence claim.
