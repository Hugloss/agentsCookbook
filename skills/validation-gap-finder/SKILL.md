---
name: validation-gap-finder
description: Designs decisive validation with observable checks, failure cases, acceptance criteria, and recovery proof.
license: MIT
---

# Validation Gap Finder

Standalone, read-only validation design for plans, changes, or implementation evidence.

## INVARIANT

> **Completion must be observable; checks must prove the behavior that matters.**

## HUNT

Hunt for:
- vague `tests pass` claims;
- missing failure/retry/recovery scenarios;
- checks that exercise artificial paths;
- acceptance criteria with no binary outcome;
- rollback/recovery that is untested or unverifiable;
- skipped checks described as success.

## PROVE

Map each important invariant or user-visible behavior to the smallest decisive check. Mark commands or paths as assumptions until verified.

## DO NOT REPORT

Do not claim proposed validation ran. Do not maximize test count. `coverage-design-review` owns the broader question of whether the test portfolio covers real behavior.

## PREFER

Use a minimum complete validation set: automated checks first, necessary manual checks only, explicit failure cases, binary exit criteria, and recovery proof when relevant.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, audit the validation actually supplied: what ran, what failed or was skipped, what behavior it proves, and what decisive checks are still missing. Never convert proposed checks into claimed evidence.

Return `# Build Validation Review` with blocking findings, non-blocking findings, missing validation/evidence, concrete checks/fixes, and remaining risk. Use `None` when complete.

## OUTPUT

Otherwise return `# Validation Design Report` with verdict, strategy, automated checks, manual checks, acceptance criteria, failure/edge scenarios, rollback verification, missing repo facts, and concrete fixes.
