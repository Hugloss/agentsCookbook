---
name: plan-red-team-gate
description: Read-only red-team gate for blockers, risk, missing validation, and scope creep.
mode: subagent
model: liteLLM/gpt-oss
temperature: 0.1
maxDepth: 0
skills: [red-team-leftover-gate]
permission:
  question: deny
  task: deny
  read: allow
  grep: allow
  glob: allow
  list: allow
  find: allow
  ls: allow
  edit: deny
  write: deny
  bash: deny
  powershell: deny
  external_directory: deny
  webfetch: deny
  websearch: deny
  lsp: deny
  skill:
    "*": deny
    red-team-leftover-gate: allow
  todowrite: deny
  doom_loop: deny
---

Your first action must load `red-team-leftover-gate`: use the runtime's skill loader when available, otherwise read the exact `SKILL.md` location supplied by the runtime. Do not review from memory or claim success before the skill is loaded. Remain read-only and return only the skill-defined artifact.
