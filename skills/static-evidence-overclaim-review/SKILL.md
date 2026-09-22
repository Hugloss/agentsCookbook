---
name: static-evidence-overclaim-review
description: Finds static or heuristic analyzers emitting exact relationships, ownership, ambiguity, or race facts beyond what their proof model can establish.
license: MIT
---

# Static Evidence Overclaim Review

Standalone, read-only analyzer soundness review.

## INVARIANT

> **Static evidence may claim only what its resolution model proves; unresolved dynamic, aliased, imported, or shadowed cases must remain qualified or unknown.**

## HUNT

Hunt for analyzers that:
- treat dynamic receiver calls as exact repository calls;
- ignore lexical shadowing or alias rebinding;
- treat imported/external methods as repository ambiguity;
- infer module/distribution ownership from fuzzy names;
- mistake fresh local copies for shared mutable state;
- classify unresolved candidates as exact relationships.

## PROVE

Construct a legal program shape the analyzer cannot disambiguate under its stated model. Show that it nevertheless emits an exact/authoritative fact rather than unknown, ambiguous, external, or bounded evidence.

## DO NOT REPORT

Do not report conservative false negatives merely because the analyzer declines to infer a relationship it cannot prove.

## PREFER

Make proof bases explicit, preserve ambiguity, distinguish external/dynamic cases, and add narrow resolvers only when exact evidence is available.

## OUTPUT

Return `# Static Evidence Overclaim Review` with analyzer claim, available proof, unresolved dimension, false exact result, safer classification, and regression.
