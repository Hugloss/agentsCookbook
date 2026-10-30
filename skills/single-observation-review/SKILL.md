---
name: single-observation-review
description: Finds logical operations that rescan, reread, reparse, or rebuild the same input world instead of reusing one artifact.
license: MIT
---

# Single Observation Review

Standalone, read-only repeated-observation review.

## INVARIANT

> **One logical operation should observe one authoritative version of its input world.**

## HUNT

Trace a real operation from source/config to discovery, reading/parsing, authoritative graph/artifact, and later stages. Hunt for:
- second dependency/include/repository walks;
- rereads or reparses;
- repeated config/capability discovery;
- equivalent graph reconstruction;
- later stages that receive raw source/path even though the analyzed artifact already exists.

## PROVE

Name one logical operation, its required observation lifetime, and the exact input scope. Trace the first and repeated reads, the artifact already available, and the extra work or inconsistent-version consequence. Prove that the first artifact can satisfy the later obligation at the required freshness; inspect whether it lacks only a small naturally owned fact. A repeated API name alone is not proof of redundant observation.

## DO NOT REPORT

Do not report trivial recalculation, reads of different scopes, intentional fresh observation after a mutation, or independent trust-boundary verification. Preserve streaming/chunked reads whose combined scope is one observation. Do not solve a second observation with a hidden cache or registry.

## PREFER

Build once, pass the exact artifact forward, and add only facts that naturally belong in that artifact. Delete duplicate walkers/readers/builders.

## OUTPUT

Return `# Single Observation Review` with operation/input scope, freshness contract, both traced observations, reusable artifact, concrete repeated work or consistency risk, smallest API correction and verification.

Use `FINDING` for proved unnecessary re-observation; `CLEAN` only when the declared operation's observation paths were traced and no unnecessary re-observation remains; `LEAVE ALONE` for independently required freshness or verification; otherwise `INSUFFICIENT EVIDENCE`. `stable-observation-snapshot-review` owns incoherent mixed generations without redundant observation.
