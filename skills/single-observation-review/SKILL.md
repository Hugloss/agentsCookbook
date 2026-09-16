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

Show first observation, second observation, why the API causes repetition, and whether inputs could change between passes. Check whether the first artifact lacks only a small fact later stages genuinely need.

## DO NOT REPORT

Do not report trivial recalculation. Do not solve a second observation with a hidden cache or registry.

## PREFER

Build once, pass the exact artifact forward, and add only facts that naturally belong in that artifact. Delete duplicate walkers/readers/builders.

## OUTPUT

Return `# Single Observation Review` with production flow, repeated observations, artifact completeness, API boundary fixes, consistency risks, removal, and one-operation verification.
