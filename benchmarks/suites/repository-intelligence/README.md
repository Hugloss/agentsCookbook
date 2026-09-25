# Repository Intelligence

This suite measures repository-intelligence correctness and its effect on coding-agent
work without making any evaluated product its own grading authority.

Hashmarks and Enola keep their native CLI/MCP semantics. The benchmark does not ETL
their facts into a shared repository graph. Only the experiment envelope is normalized:
participant identity, tool exposure/adoption, execution evidence, budgets,
contamination, independent grading, receipts, and reporting.

## pilot-v1

`pilot-v1/` is the first executable harness qualification. It freezes three tasks on
one exact agentsCookbook commit/tree and compares bare, Hashmarks, and Enola using the
Codex host-default model.

It remains immutable historical evidence. Do not retrofit explicit model identity into
v1.

## agent-matrix-v2

`agent-matrix-v2/` freezes a new experiment version on the merged v1 implementation
bytes. It keeps the same three task families and expands to two explicit model/provider
conditions through the same Codex execution runtime:

- `gpt-5.6-sol` with high reasoning effort;
- local Ollama `gemma4:12b`.

Each model runs bare, with Hashmarks, and with Enola, producing 18 frozen definitions.

The main comparison is assistance gain **within one model/runtime**:

- bare → Hashmarks;
- bare → Enola.

Cross-model rows are descriptive only. They are useful for asking whether repository
intelligence helps a smaller local model differently from a frontier hosted model, but
hardware, inference backend, model architecture, and model size remain confounders.

The local-model admission path records Ollama executable identity and a digest of the
exact installed model descriptor. Missing local infrastructure is `INCOMPLETE`, not
`FAIL`.

## Measurement boundary

The suites measure correctness, subject availability, MCP configuration/adoption,
command/tool calls, MCP evidence bytes, token usage, duration, contamination, and
oracle health.

Codex JSONL does not expose authoritative repository file-read bytes, so these suites
explicitly mark that archaeology metric unavailable rather than estimating it.

Do not publish an overall winner score. Report per-task/per-condition evidence,
paired assistance deltas over the same-model bare condition, and descriptive
cross-agent observations.
