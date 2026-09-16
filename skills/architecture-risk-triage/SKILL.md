---
name: architecture-risk-triage
description: Routes evidence-backed architecture hotspots to the narrow specialist review that can prove the actual failure class.
license: MIT
---

# Architecture Risk Triage

Standalone, read-only discovery/router skill. It identifies where to aim deeper review; it is not a generic architecture rewrite.

## INVARIANT

> **Do not perform a vague architecture review when a sharper specialist can prove the problem.**

## HUNT

Trace important production paths and hunt strong signals:
- stale async completion;
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

## DO NOT REPORT

Do not deeply solve every category. Do not rank files by size or complexity aesthetics. Do not create findings merely to fill a quota.

## PREFER

Route each hotspot to the narrowest skill. Protect coherent owners and explicitly say when no specialist review is justified.

## OUTPUT

Return `# Architecture Risk Triage` with evidence-backed hotspots and routing. Use exact skill names and a one-sentence reason for each route.
