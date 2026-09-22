---
name: negative-evidence-admissibility-review
description: Finds absence or no-finding claims treated as evidence despite unknown, incomplete, truncated, or undeclared observation scope.
license: MIT
---

# Negative Evidence Admissibility Review

Standalone, read-only absence-evidence review.

## INVARIANT

> **Absence is evidence only inside an explicit observation scope proven complete and non-truncated for the fact being negated.**

## HUNT

Hunt for:
- empty result sets interpreted as not-present;
- caller-claimed complete data with unknown truncation;
- bounded scans used to prove repository-wide absence;
- missing dependency/module/relationship evidence interpreted as negative ownership;
- partial logs or telemetry used to prove an event did not occur;
- unobserved data collapsed into false/no.

## PROVE

Name the negative claim and its required universe. Show that scope, completeness, or truncation is missing/insufficient while downstream code still treats absence as affirmative evidence.

## DO NOT REPORT

Do not report positive evidence or explicitly best-effort absence that remains labeled unknown/incomplete and cannot authorize a decision.

## PREFER

Carry scope, completeness, and truncation independently. Admit negative evidence only after all required dimensions prove the observed universe is sufficient.

## OUTPUT

Return `# Negative Evidence Admissibility Review` with negative claim, required scope, observed scope, completeness/truncation state, false inference, correction, and verification.
