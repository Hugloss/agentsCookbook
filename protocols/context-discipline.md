# Agent Context Discipline

This protocol is reusable guidance for working with the context supplied
by an agent host. It is **not** a token-window configuration, an admission
gate, a fixed working-set budget, or a requirement on any model.

The model provider and runtime (such as OpenCode or Pi) own their context
window, output limits, compaction and other context-management settings.
When these are not exposed to the agent, the agent must not invent them.
The agent should choose useful evidence, request more when warranted,
and rely on the host's supported session/compaction behavior as needed.
Do not discard material evidence just to satisfy an invented token target.

For observed context usage in evaluations, see
[EvalShot](https://github.com/Hugloss/EvalShot/blob/main/docs/model-context-observation.md).
EvalShot does not set a global model context size.

## Prompt description conventions

- Prefer short descriptions that state the capability and selection trigger.
- Keep descriptions within the existing repository and host compatibility
  contracts; procedures belong in the body.

## Evidence and history handling

- Work from the current task and current repository bytes, not superseded drafts.
- Prefer verified facts and exact source references over raw exploration logs.
- Keep material finding receipts accessible; inspect full evidence when needed.
- Avoid bulk-loading unrelated prior reports and repository-wide dumps.
- State when a required fact or context measurement is unknown.
- Let the agent choose the evidence detail needed for the task; preserve
  correctness and traceability rather than enforcing an arbitrary context cap.

Run artifacts may retain detail outside the active conversation. Reusing a
relevant artifact should be a deliberate evidence choice, not an obligatory
full reload or an automatic loss of detail.
