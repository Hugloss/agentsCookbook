---
name: alternate-path-removal-review
description: Finds obsolete or parallel architecture paths that remain callable after a canonical implementation already exists.
license: MIT
---

# Alternate Path Removal Review

Standalone, read-only canonical-path cleanup review.

## INVARIANT

> **Once a canonical architecture exists, obsolete alternatives should stop existing.**

## HUNT

Hunt for V1/V2 paths, legacy stores, compatibility adapters, fallback readers, deprecated controllers, duplicate serializers, old execution modes, direct bypasses, unused providers, and migration-era runtime paths.

## PROVE

Establish the current canonical path and support/removal policy independently of names such as legacy or V2. Trace alternate callers, dynamic registration and external compatibility obligations; compare observable contracts. Show why the alternate is obsolete and how every supported caller can move without losing required behavior. A repository search that finds no local caller does not establish absence of external consumers.

## DO NOT REPORT

Do not merge genuinely different workflows. Preserve a currently supported public interface, explicit migration/rollback window, or fallback required by the failure contract. Old age, a legacy name, or a newer implementation alone does not prove removability.

## PREFER

When the support contract permits it, move controlled callers to the canonical path and delete the obsolete alternate. Do not retain pass-through aliases or synchronized legacy mirrors without an actual supported obligation. Name any remaining external migration obligation instead of guessing it away.

## OUTPUT

Return `# Alternate Path Removal Review` with canonical/alternate map, support authority, inspected callers, contract differences, justified retention or deletion, migration order and verification needed.

Use `FINDING` for a proven obsolete path with a safe caller migration; `CLEAN` only when the declared path/caller inventory is complete and no unsupported obsolete path remains; `LEAVE ALONE` for a current supported distinction; otherwise `INSUFFICIENT EVIDENCE`. Do not claim an alternate is absent until the deletion and relevant discovery checks actually occurred.
