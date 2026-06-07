---
name: validation-gap-finder
description: Validation quality checklist. Use when designing or reviewing tests, manual checks, acceptance criteria, failure scenarios, rollback verification, or missing validation gaps in an implementation plan.
license: MIT
---

# Validation Gap Finder

Behavioral guidelines for turning a plan into verifiable checks.

**Tradeoff:** This skill biases toward observable pass/fail criteria over speed. For tiny docs-only changes, keep validation lightweight but still concrete.

## 1. Make Checks Executable

Validation should name real commands or clearly mark assumptions.

Check for:
- Existing smoke, lint, build, test, or preflight commands.
- Targeted file or config parsing when there is no test suite.
- Manual checks only when automation is unavailable or not worth the cost.
- Reasons for skipped checks.

## 2. Require Binary Acceptance Criteria

Every acceptance criterion must be answerable with yes or no.

Replace vague wording:
- "better validation" -> "preflight fails when a reviewer skill permission is missing"
- "docs are updated" -> "README mentions the new skill install path"
- "works correctly" -> "opencode debug skill lists every expected skill name"

## 3. Cover Failure Scenarios

Look beyond the happy path:
- Missing file, missing symlink, wrong prompt path, or wrong permission.
- Existing conflicting global files.
- Running OpenCode sessions holding stale config.
- Local config and global symlink paths diverging.

## 4. Verify Rollback

Rollback validation should say how to prove recovery worked.

Useful checks:
- Unlink removes only cookbook-owned symlinks.
- Real user files and unrelated symlinks are preserved.
- Re-running link is idempotent.
- The old behavior can be restored by reverting the repo change and relinking.

## 5. Report Gaps With Fixes

For every validation gap, include:
- Severity.
- Plan step or section.
- Why it matters.
- The exact check or acceptance criterion to add.
