# Repository Intelligence

This suite measures repository-intelligence correctness and its effect on coding-agent
work without making any evaluated product its own grading authority.

The initial subjects are bare/no repository intelligence, Hashmarks, and Enola. Codex
is the first agent adapter; a local-model adapter is the next genericity expansion
after the executable pilot is qualified.

## Pilot v1

`pilot-v1/` freezes three tasks on one exact agentsCookbook commit/tree:

- two read-only owner/localization questions with independent exact-answer oracles;
- one injected receipt-completion defect with a pre-existing focused regression oracle.

Across bare, Hashmarks, and Enola this yields nine paired trial definitions.

The pilot measures correctness, subject availability, MCP configuration/adoption,
command/tool calls, MCP evidence bytes, token usage, duration, contamination, and
oracle health. Codex JSONL does not expose authoritative repository-read bytes, so the
pilot explicitly marks that archaeology metric unavailable rather than estimating it.

See `pilot-v1/README.md` for the exact replay and reporting commands.

Do not publish an overall winner score. Report per-task/per-condition evidence and
paired assistance deltas over the same-agent bare condition.
