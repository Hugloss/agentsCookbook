---
name: evidence-provenance-binding-review
description: Finds reusable evidence or receipts whose identity omits source, scope, producer, policy, generation, environment, or mode needed for interpretation.
license: MIT
---

# Evidence Provenance Binding Review

Standalone, read-only evidence provenance review.

## INVARIANT

> **Reusable evidence must cryptographically or structurally bind every authority-bearing dimension required to interpret it.**

## HUNT

Hunt in receipts, attestations, benchmark results, cached evidence, CI artifacts, and handoffs for missing binding to:
- repository/source identity;
- task or request;
- policy/configuration;
- proof scope and completeness;
- generation/revision;
- producer/tool/schema;
- execution environment or mode when results depend on them;
- exact corpus or membership.

## PROVE

Construct two materially different provenance contexts that can produce the same apparent evidence identity or be substituted without rejection. Show the incorrect reuse path.

## DO NOT REPORT

Do not demand provenance fields that cannot affect interpretation or authority. Informational logs that make no reusable proof claim are out of scope.

## PREFER

Bind provenance into one canonical evidence identity and validate it before reuse. Separate stale, invalid, foreign, and current evidence.

## OUTPUT

Return `# Evidence Provenance Binding Review` with evidence artifact, missing provenance dimension, substitution/reuse path, authority consequence, required binding, verification.
