---
name: semantic-redecision-review
description: Finds places where the same semantic fact or policy decision is independently interpreted more than once.
license: MIT
---

# Semantic Redecision Review

Standalone, read-only semantic consolidation review.

## INVARIANT

> **A semantic fact should be decided once and consumed afterward.**

## HUNT

Hunt for repeated decisions about:
- eligibility, readiness, success/failure, status meaning;
- capability, admission, placement, policy, classification, canonical identity;
- equivalent conditionals or normalizers in callers and owners;
- raw ingredients passed downstream so each layer can decide again.

## PROVE

Prove two paths answer the same semantic question. Trace where the first authoritative answer exists and where later code reinterprets it. Distinguish semantic interpretation from integrity validation and display derivation.

## DO NOT REPORT

Do not report repeated syntax, trust-boundary validation, or genuinely distinct domain decisions.

## PREFER

Preserve one explicit semantic result and pass it forward. Delete downstream classifiers, branches, and reconstruction helpers that become unnecessary.

## OUTPUT

Return `# Semantic Redecision Review` with findings: semantic question, first authority, duplicate decisions, real consequence, canonical result, code that can disappear, verification.
