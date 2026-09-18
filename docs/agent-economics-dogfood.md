# Agent Economics real-agent dogfood gate

This empirical P10/P11 closeout gate is intentionally separate from the deterministic regression suite.

## Purpose

Prove that a coding agent can use the capability bridge for local inspect → verify → repair → verify loops without using CI/CD as the repair executor. The external coding agent owns every source edit. Agent Economics owns only bounded evidence and execution of explicitly selected repository commands.

## Required paired tasks

Run the same starting repository bytes in baseline and bridge modes for:

1. localized assertion failure;
2. import/collection or syntax failure;
3. affected-dependent / wrong-test-selection failure;
4. focused PASS followed by a broader repository-gate failure.

Hashmarks is the primary real-world dogfood repository. At least one complete pair must also run in an independent repository, preferably Oh-Goon, using that repository's own declared verification authority.

## Strict closeout records

Exploratory P11 records may remain partial. A pair used to close this gate must pass:

```bash
python -m agent_economics benchmark-outcomes \
  --input outcomes.jsonl \
  --strict-dogfood
```

Strict mode fails closed unless baseline and bridge bind the same non-null repository, task-fixture/corpus, initial-source, agent-profile, and execution-environment identities. The two modes must have distinct run identities. Both outcomes must bind final-source and independent CI evidence and prove the oracle was opened only after the outcome was frozen. The bridge outcome must additionally bind the exact Agent Economics implementation, command manifest, local qualification, and a known local-vs-CI agreement result.

A task specification identity does **not** substitute for the initial-source identity. The latter binds the actual starting defect/repository bytes used by both modes.

## Measurement fairness

Use the same counting method in both modes for files opened, evidence bytes, context estimate, tool calls, local commands, repair iterations, verification attempts, failed edits, and time to first correct edit. Use fresh isolated worktrees/sessions so artifacts, prior edits, or previous-run evidence cannot leak between modes. Keep host permissions and repository/tool supply equivalent; the intended treatment difference is Agent Economics use.

Freeze each outcome before opening the oracle. Retain failed and unfavorable pairs rather than rerunning and discarding them. Benchmark output is measurement evidence, never an automatic promotion or release verdict.

## Hard rules

- Repository bytes must be locally materialized to the coding agent.
- No temporary CI workflow may be used for repair iterations.
- The bridge must not edit source or install dependencies.
- Focused PASS is not repository qualification.
- Run CI only after local outcome freeze as an independent comparison.
- Any local/CI disagreement must be recorded; unknown agreement cannot close the gate.
- Missing strict receipts make the pair incomplete.
- Temporary `.agent-economics/` and `.agent-artifacts/` materialization must remain untracked in consumer repositories.
- Do not add Hashmarks-specific policy or parsing to Agent Economics to make dogfood pass.

## Current repository qualification

The permanent GitHub workflow runs compile checks plus the complete deterministic Agent Economics qualification corpus. Those checks validate the bridge implementation but **do not substitute for this real-agent dogfood gate**.

A ChatGPT session that has only GitHub/API access and no locally materialized checkout must report `repository_bytes_unavailable`; it cannot truthfully complete this gate.
