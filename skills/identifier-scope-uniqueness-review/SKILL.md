---
name: identifier-scope-uniqueness-review
description: Finds identifiers used as keys, identities, or deduplication handles without proving uniqueness in the exact scope where that use requires it.
license: MIT
---

# Identifier Scope Uniqueness Review

Standalone, read-only identifier semantics review.

## INVARIANT

> **An identifier may act as identity only inside a scope where its required uniqueness is explicitly guaranteed and enforced.**

## HUNT

Hunt for:
- event serials assumed globally unique when only stream-local;
- duplicate bundle, anchor, node, item, or member IDs silently overwriting map entries;
- IDs unique per producer reused as cross-producer keys;
- deduplication on descriptive names;
- uniqueness checked in one scope but consumed in a broader scope;
- dictionary/set conversion that silently collapses duplicates.

## PROVE

Construct two distinct entities with the same identifier inside the consumer's effective scope. Show overwrite, collapse, false correlation, or ambiguous lookup.

## DO NOT REPORT

Do not report duplicate descriptive labels when they are never used as identity, key, deduplication handle, or authority evidence.

## PREFER

Name the uniqueness scope explicitly, enforce it at admission, and use composite/canonical identity when a broader scope is required.

## OUTPUT

Return `# Identifier Scope Uniqueness Review` with identifier, promised scope, consumer scope, collision path, consequence, corrected identity, and verification.
