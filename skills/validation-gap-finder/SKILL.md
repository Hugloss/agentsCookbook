---
name: validation-gap-finder
description: Designs decisive validation with observable checks, failure cases, acceptance criteria, and recovery proof.
license: MIT
---

# Validation Gap Finder

Standalone, read-only validation design for plans, changes, or implementation evidence.

## INVARIANT

> **Completion must be observable; the minimum validation set must cover the behavior obligations established by the user request and repository-owned contracts.**

## HUNT

Hunt for:
- vague `tests pass` claims;
- validation scope chosen only from the checks that already pass;
- missing failure/retry/recovery scenarios;
- checks that exercise artificial paths;
- acceptance criteria with no binary outcome;
- rollback/recovery that is untested or unverifiable;
- skipped checks described as success.

## PROVE

Establish the behavior obligations from the user request, repository contracts, and authoritative acceptance/qualification policy before selecting checks. Map each required invariant or user-visible behavior to the smallest decisive check. Mark commands, paths, or obligations as assumptions until verified.

## DO NOT REPORT

Do not claim proposed validation ran. Do not maximize test count. Do not add checks for behavior outside the declared obligation set merely because more testing is possible. `coverage-design-review` owns the broader question of whether the test portfolio covers real behavior.

## PREFER

Use the minimum **complete** validation set over the authoritative obligation set: automated checks first, necessary manual checks only, explicit failure cases, binary exit criteria, and recovery proof when relevant. Do not shrink the obligation set after observing failures.

## BUILD REVIEW MODE

When input starts with `BUILD REVIEW MODE`, audit the validation actually supplied against the pre-established behavior obligations: what ran, what failed or was skipped, what behavior it proves, and what decisive checks are still missing. Never convert proposed, skipped, unavailable, or incomplete checks into claimed evidence.

Return `# Build Validation Review` with validation obligations, blocking findings, non-blocking findings, missing validation/evidence, concrete checks/fixes, and remaining risk. Use `None` only when every required obligation in scope has decisive evidence.

## OUTPUT

Otherwise return `# Validation Design Report` with authoritative behavior obligations, verdict, strategy, automated checks, manual checks, acceptance criteria, failure/edge scenarios, rollback verification, missing repo facts, and concrete fixes.
