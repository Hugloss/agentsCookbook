---
name: stable-observation-snapshot-review
description: Finds multi-read observations that combine facts from different revisions or generations without binding them to one stable snapshot.
license: MIT
---

# Stable Observation Snapshot Review

Standalone, read-only observation-consistency review.

## INVARIANT

> **One logical observation must describe one coherent source state, not a mixture of facts read from different revisions or generations.**

## HUNT

Hunt for:
- metadata read before content with no revision revalidation;
- several repository queries in one decision using different generations;
- bytes and locator/range information observed from moving files independently;
- related evidence packets assembled across unsynchronized refreshes;
- caches reused inside an otherwise snapshot-bound decision without generation binding;
- concurrent initialization/publication exposing mixed schema or state.

## PROVE

Construct or trace an interleaving where source state changes between component reads. Show the final observation combines mutually incompatible facts while still presenting itself as one coherent result.

## DO NOT REPORT

Do not report explicitly streaming/eventual-consistency APIs that declare per-item revisions and never claim a coherent snapshot.

## PREFER

Bind observations to one generation/revision, use stable read primitives, revalidate moving inputs, and carry snapshot identity through derived projections.

## OUTPUT

Return `# Stable Observation Snapshot Review` with logical observation, component reads, revision/generation mismatch, impossible combined result, correction, and verification.
