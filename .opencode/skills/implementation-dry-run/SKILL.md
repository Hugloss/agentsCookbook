---
name: implementation-dry-run
description: Implementation simulation checklist. Use when dry-running a plan for missing steps, unclear file ownership, sequencing mistakes, infeasible validation, dependency assumptions, or forgotten follow-up work.
license: MIT
---

# Implementation Dry Run

Behavioral guidelines for simulating implementation before anyone edits files.

**Tradeoff:** This skill biases toward operational detail over brevity. Keep findings focused on steps that would make an implementer guess.

## 1. Walk The Plan In Order

Mentally execute each step:
- What file or area is touched?
- What exact behavior changes?
- What must already exist?
- What validation proves the step worked?

If an answer is missing, report an ambiguous step.

## 2. Check File Ownership

Identify who should own each change:
- Primary build agent owns edits.
- Planning coordinator owns only written plans.
- Reviewer subagents supply evidence only.
- Skills guide behavior and do not replace prompts or agents.

Flag any step that delegates edits to a read-only reviewer.

## 3. Check Sequencing

Make sure prerequisites happen first:
- Create skill files before linking them.
- Add asset lists before link/unlink loops rely on them.
- Update examples before preflight expects new permission shapes.
- Restart OpenCode after config, prompt, agent, or skill changes.

## 4. Check Validation Feasibility

Validation must be possible in the described environment.

Flag:
- Commands that do not exist.
- Tests requiring missing setup.
- Full preflight blocked by running OpenCode processes without an override.
- Checks that require global relinking but only local files changed.

## 5. Produce Concrete Fixes

For every dry-run issue:
- Name the missing or ambiguous step.
- Explain the failure mode.
- Give the exact plan text or check to add.
