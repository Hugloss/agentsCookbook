# Active Context Discipline

This protocol belongs to the reusable Agents Cookbook prompts and adapters.
It specifies **how to use** available context, not the maximum context size
of a particular model, provider, experiment or host.

The runtime/operator selects the model and its available context window.
The reviewer must stay within that configured limit, reserve space for tools,
reasoning and completion, and disclose unknown usage rather than claim a
token-budget qualification it did not measure.

Concrete model profiles, numerical ceilings, reserve targets, tokenizer
measurements and empirical context qualification are owned by
[EvalShot](https://github.com/Hugloss/EvalShot/blob/main/docs/context-profiles.md).
They are not installation or preflight prerequisites for using a cookbook
skill, agent or flow.

## Description economics

- preferred agent/skill description: 120 characters or fewer
- repository maximum: 160 characters
- external OpenCode/Pi compatibility limits remain ceilings, not writing targets

Descriptions contain capability and selection trigger only. Procedure
belongs in the body.

## Active-context rules

- current subject beats historical drafts;
- compact verified facts beat raw exploration logs;
- material finding receipts beat full sibling reports;
- selected evidence beats repository-wide dumps;
- explicit unknowns beat guessed context;
- reserve completion/tool headroom before adding optional evidence.

A run artifact store may preserve detail outside active context, but final
synthesis must not reload every artifact indiscriminately.
