---
name: repeated-test-setup-review
description: Finds expensive application, database, repository, browser, or fixture setup rebuilt across tests without semantic need.
license: MIT
---

# Repeated Test Setup Review

Standalone, read-only test-construction cost review.

## INVARIANT

> **Repeated setup should represent required isolation, not repeated architecture construction.**

## HUNT

Measure setup separately from behavior execution. Hunt repeated app bootstrap, DB/schema setup, repository indexing, config loading, dependency discovery, browser/server startup, auth/session setup, and large fixture graph construction.

## PROVE

For each repeated setup prove whether isolation truly requires it or production objects are unnecessarily expensive to construct. Identify the smallest real dependency the behavior needs.

## DO NOT REPORT

Do not trade isolation for hidden shared mutable fixtures. Do not report clean-room setup that is essential to the integration behavior.

## PREFER

Prefer cheap production construction, narrow fixtures, and explicit dependencies. Share only immutable/safely isolated setup.

## OUTPUT

Return `# Repeated Test Setup Review` with measured setup costs, repetition count, required-vs-accidental setup, production cause, simplification, and remeasurement.
