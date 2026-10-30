---
name: test-work-amplification-review
description: Finds tests whose small behavioral assertion triggers disproportionate production work and traces the architectural cause.
license: MIT
---

# Test Work Amplification Review

Standalone, read-only review of avoidable test and production work.

## INVARIANT

> **A test should pay only for the behavior it proves.**

## HUNT

Start with available timing evidence or inspect the requested test paths directly. Hunt for repository-wide scans, filesystem/subprocess work, full bootstrap, repeated parsing, excessive database setup, broad validation, unrelated integration work, and repeated production operations. Timing collection is not a prerequisite for removing demonstrably unnecessary work.

## PROVE

Show `test → behavior → production path → repeated or broad work` and why that work is unnecessary for the established assertion or integration contract. Trace frequency, input size, or unrelated operations where timing is unavailable; a slow-looking name or test duration alone does not prove amplification. Separate fixture overhead from production cost and preserve required failure detection.

## DO NOT REPORT

Do not report a legitimately expensive integration test when the cost is exactly what it exists to verify. Do not make tests faster by mocking away meaningful behavior.

## PREFER

Remove unnecessary work at its actual production or fixture owner. Keep assertions, isolation, and behavioral fidelity. Verify the affected behavior after the change; measure before/after only when a quantified speedup or performance budget must be established. Do not invent savings from a shorter test body.

## OUTPUT

Return `# Test Work Amplification Review` with inspected tests, asserted behavior, avoidable work path, evidence, smallest correction, and functional verification. Separate observed timings from inferred cost shape.

Report `FINDING` only for proved unnecessary work. A scoped `CLEAN` requires the selected assertions and their setup/production paths to be traced; `LEAVE ALONE` fits work required by the real integration contract. Unavailable cost attribution or behavioral purpose remains `INSUFFICIENT EVIDENCE`, not a fabricated optimization.
