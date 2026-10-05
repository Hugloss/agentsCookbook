# Context-invariance repository-intelligence benchmark v1

This research suite tests whether irrelevant or untrusted prompt context changes a
coding agent's repository-intelligence decision when the repository bytes, task,
oracle, subject, agent, budgets, and paired replicate identity remain fixed.

## Claim boundary

The primary observation is a **within-agent, within-subject, within-task paired
semantic transition**. Cross-agent rows are descriptive only. The suite does not rank
models or products and has no release authority.

Each counterfactual set contains four prompt contexts:

- `neutral` — the task exactly as frozen;
- `placebo` — unrelated organizational background;
- `authority-claim` — an unsupported senior-maintainer claim pointing at the wrong file;
- `misleading-hint` — a prior-investigation claim pointing at the wrong symbol.

The harness resolves the effective prompt once from the frozen task and condition.
Context text is prefixed so the original task and its output contract remain byte-for-byte
identical and last in every non-neutral prompt.

## Frozen population

The suite reuses two deterministic heldout-v1 localization authorities on the same
pinned Hashmarks repository tree:

- `locate-prefix-path-enumerator`;
- `locate-repository-content-identity`.

It runs bare and Hashmarks-assisted conditions under Codex-native and OpenCode-native,
with three paired replicate IDs per context. That produces **96 executions** and,
when complete, **72 neutral-to-context comparisons**.

## Evidence and stability

Reports retain ordinary sealed trial receipts and add:

- exact-text `answer_flip_rate`;
- semantic-success `semantic_flip_rate`;
- observed tool-sequence `route_flip_rate`;
- selected-subject invocation `authority_flip_rate`;
- explicit `benchmark-counterfactual-pair.v1` pair identities;
- neutral→variant semantic transitions and context-change summaries.

Flip rates are pairwise disagreement among observed replicates. Missing route or
subject-invocation observability stays unknown; it is never converted to zero.

## Analysis contract

The frozen analysis contract requires three observed replicates per variant arm and at
least 18 comparable neutral↔variant pairs for the selected lane. Below that threshold,
results remain descriptive-only. Meeting the threshold does not authorize statistical
significance claims or cross-agent ranking.

## Known limitations

The context variants intentionally test prompt sensitivity, not adversarial security.
A changed route with preserved semantics is evidence of behavioral sensitivity, not by
itself a defect. The deterministic repository-location oracle grades the final semantic
answer; it does not judge reasoning quality.

Use the normal benchmark workflow with this suite's `experiment.json` and
`score.py`. Keep campaign roots separate from heldout and behavioral suites.
