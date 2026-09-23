# Agent Economics real-agent dogfood gate

This empirical P10/P11 closeout gate is intentionally separate from the deterministic regression suite.

## Purpose

Prove that a coding agent can use the capability bridge for local inspect → verify → repair → verify loops without using CI/CD as the repair executor. The external coding agent owns every source edit. Agent Economics owns only bounded evidence and execution of explicitly selected repository commands.

## Required paired tasks

Run the same starting repository bytes in baseline and bridge modes for the four primary Hashmarks scenarios:

1. localized assertion failure;
2. import/collection or syntax failure;
3. affected-dependent / wrong-test-selection failure;
4. focused PASS followed by a broader repository-gate failure.

At least one additional complete pair must run against an independent repository, preferably Oh-Goon, using that repository's own declared verification authority.

The immutable dogfood corpus includes a dedicated `affected-dependent` fixture class so this closeout requirement is not hidden inside a generic benchmark task.

## Per-pair strict records

Exploratory records may remain partial. Every pair admitted to the final campaign must first pass:

```bash
python -m agent_economics benchmark-outcomes \
  --input outcomes.jsonl \
  --strict-dogfood
```

Per-pair strict mode fails closed unless baseline and bridge bind the same non-null repository, task-fixture/corpus, initial-source, agent-profile, and execution-environment identities. The two modes must have distinct run identities. Both outcomes bind final-source and independent CI evidence and prove the oracle was opened only after the outcome was frozen. The bridge outcome additionally binds the exact Agent Economics implementation, command manifest, local qualification, and a known local-vs-CI agreement result.

A task specification identity does **not** substitute for the initial-source identity. The latter binds the actual starting defect/repository bytes used by both modes.

## Final campaign gate

Per-pair validity is necessary but not sufficient. The complete closeout must also supply a campaign manifest and pass:

```bash
python -m agent_economics dogfood-campaign \
  --outcomes outcomes.jsonl \
  --campaign campaign.json \
  --artifact campaign-result.json
```

The campaign manifest is `agent-economics-dogfood-campaign` v1 and fails closed unless it binds:

- one exact campaign, Agent Economics implementation, corpus, and measurement-contract identity;
- each of the four required primary scenarios **exactly once**;
- at least one pair from a repository different from the primary repository;
- exact campaign membership matching the outcome pairs, so unfavorable rows cannot be silently omitted;
- globally unique baseline/bridge session/run identities;
- globally unique baseline/bridge isolation, freeze, and post-freeze oracle-access receipt identities;
- the same measurement-contract identity for every campaign task;
- cleanup evidence for every participating consumer repository;
- final agentsCookbook CI evidence bound to the exact campaign implementation identity.

The campaign validator reuses strict per-pair validation first. It does not turn empirical evidence into automatic release, merge, edit, or execution authority.

## Measurement fairness

Use the same bound measurement contract in both modes for files opened, evidence bytes, context estimate, tool calls, local commands, repair iterations, verification attempts, failed edits, and time to first correct edit. Use fresh isolated worktrees/sessions so artifacts, prior edits, or model memory cannot leak between modes. Keep host permissions and repository/tool supply equivalent; the intended treatment difference is Agent Economics use.

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
- A campaign manifest can bind session-isolation evidence, but it cannot manufacture independent agent sessions. The producer of that evidence must actually enforce the claimed isolation.

## Current repository qualification

The permanent GitHub workflow runs compile checks plus the complete deterministic Agent Economics qualification corpus, including adversarial campaign-gate regressions. Those checks validate the bridge and closeout validator implementation but **do not substitute for real-agent campaign evidence**.

A session that cannot create genuinely independent agent sessions must not self-attest that model-memory isolation exists. It may prepare or validate campaign evidence, but it cannot truthfully close that empirical condition by itself.
