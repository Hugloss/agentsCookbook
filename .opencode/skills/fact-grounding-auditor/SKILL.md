---
name: fact-grounding-auditor
description: Factual grounding checklist. Use when auditing a plan or implementation for unsupported repo claims, nonexistent files or commands, guessed architecture, stale paths, or unlabeled uncertainty.
license: MIT
---

# Fact Grounding Auditor

Behavioral guidelines for separating repo facts from assumptions.

**Tradeoff:** This skill biases toward verified claims over confident prose. Do not require proof for obvious language facts, but verify repo-specific claims that drive implementation.

## 1. Separate Facts From Assumptions

Treat a claim as a repo fact only when it is backed by inspected files, command output, or provided context.

Label as assumption when:
- A path probably exists but was not inspected.
- A command is plausible but unverified.
- Tool behavior is inferred from docs or examples.
- Runtime discovery depends on user configuration.

## 2. Verify Referenced Assets

Check that named assets are real or planned:
- Agent files.
- Prompt files.
- Skill folders and `SKILL.md` files.
- Example configs.
- Link, unlink, smoke, preflight, and session-check scripts.

Flag typos and stale names.

## 3. Audit Commands

For validation commands:
- Confirm the command exists when possible.
- Mark commands that require global state, network, or a quiet OpenCode process.
- Distinguish local JSON parsing from effective OpenCode runtime checks.
- Do not present a skipped check as passed.

## 4. Check Permission Claims

Permissions are facts only when backed by config or `opencode debug agent`.

Look for:
- A prompt allowing a tool that config denies.
- A config allowing a tool that prompt says not to use.
- Broad skill access when only one specialty skill should be allowed.
- Read-only reviewers gaining edit, bash, or task access.

## 5. Fix Unsupported Claims

For every factual issue:
- Quote or name the unsupported claim.
- State what evidence is missing.
- Suggest either verifying it or relabeling it as an assumption.
