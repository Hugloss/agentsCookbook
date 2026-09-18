# Agent Economics real-agent dogfood gate

This gate is intentionally separate from the deterministic P1–P11 regression suite.

## Purpose

Prove that a coding agent can use the capability bridge for local inspect → verify → repair → verify loops without using CI/CD as the repair executor. The external coding agent owns every source edit. Agent Economics owns only bounded evidence and execution of explicitly selected repository commands.

## Required paired tasks

Run the same repository/fixture bytes in baseline and bridge modes for:

1. localized assertion failure;
2. import/collection or syntax failure;
3. affected-dependent / wrong-test-selection failure;
4. focused PASS followed by a broader repository-gate failure.

For each pair record the P11 v2 fields, including repository ID, task fixture ID, agent profile, treatment ID, CI activations, evidence/context consumption, tool calls, local commands, repair iterations, verification attempts, failed edits, time to first correct edit, bridge overhead, final correctness, and local-vs-CI agreement.

## Hard rules

- Repository bytes must be locally materialized to the coding agent.
- No temporary CI workflow may be used for repair iterations.
- The bridge must not edit source or install dependencies.
- Focused PASS is not repository qualification.
- Run CI once after local qualification as an independent comparison.
- Any local/CI disagreement must be recorded; do not discard failed pairs.
- Do not claim an economics improvement unless the paired evidence supports it.

## Current repository qualification

The permanent GitHub workflow runs compile checks plus the complete P1–P11 deterministic qualification corpus, including the pre-PR adversarial cases. Those checks validate the bridge implementation but **do not substitute for this real-agent dogfood gate**.

A ChatGPT session that has only GitHub/API access and no locally materialized checkout must report `repository_bytes_unavailable`; it cannot truthfully complete this gate.
