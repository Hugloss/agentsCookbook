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

For each alternate show canonical path, alternate path, current callers, any real contract difference, and why it still exists. Prove whether remaining callers can move.

## DO NOT REPORT

Do not merge genuinely different domain workflows merely because they look similar.

## PREFER

Move callers to the canonical path and delete the alternate. Do not leave pass-through aliases, deprecation wrappers, or synchronized legacy mirrors for code under repository control.

## OUTPUT

Return `# Alternate Path Removal Review` with canonical/alternate map, remaining callers, differences, deletion candidates, migration order, and proof the alternate is absent.
