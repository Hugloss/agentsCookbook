---
name: path-scope-confinement-review
description: Finds path normalization, mapping, symlink, or locator logic that can escape the declared repository, workspace, tenant, or authority root.
license: MIT
---

# Path Scope Confinement Review

Standalone, read-only path and namespace boundary review.

## INVARIANT

> **A path or locator admitted inside one authority root must remain inside that root after every normalization, mapping, resolution, and symlink step.**

## HUNT

Hunt for:
- `..` traversal after prefix mapping;
- longest-prefix mistakes in overlapping path maps;
- Windows/WSL/container path translation that drops root identity;
- symlink resolution performed after an insufficient lexical check;
- absolute paths accepted without rebinding to the declared repository/workspace;
- normalized paths reused across tenants, repositories, or analysis scopes;
- whole-member or locator evidence escaping the admitted source universe.

## PROVE

Start with an input accepted by the boundary and trace each normalization/mapping/resolution stage. Construct a path that reaches outside the declared root, or show that two different roots collapse to the same admitted locator.

## DO NOT REPORT

Do not report deliberate cross-root access when the caller has explicit authority for every root and the contract preserves which root each path belongs to.

## PREFER

Canonicalize once, resolve against an explicit root, apply deterministic longest-prefix mapping, re-check confinement after symlink/realpath resolution, and retain root identity in downstream evidence.

## OUTPUT

Return `# Path Scope Confinement Review` with input path, authority root, transformation chain, escape/collision point, consequence, corrected confinement boundary, and verification.
