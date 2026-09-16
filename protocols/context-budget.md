# Local-Model Context Budget

The supported local profile assumes a maximum context of 98,304 tokens.

This is a ceiling, not a target.

## Operating targets

- model maximum: 98,304
- normal working target: about 65,536 or less
- workflow hard target: about 73,728 or less
- reserve: about 24,576 for tool schemas, evidence variance, reasoning/compaction, and final output

These are design targets rather than tokenizer-independent exact limits. Deterministic gates measure characters/bytes; runtime qualification also measures the actual deployed tokenizer when available.

## Description economics

- preferred agent/skill description: <= 120 characters
- repository maximum: <= 160 characters
- external OpenCode/Pi compatibility limit remains a ceiling, not a writing target

Descriptions contain capability + selection trigger only. Procedure belongs in the body.

## Active-context rules

- current subject beats historical drafts;
- compact verified facts beat raw exploration logs;
- material finding receipts beat full sibling reports;
- selected evidence beats repository-wide dumps;
- explicit unknowns beat guessed context;
- reserve completion/tool headroom before adding optional evidence.

A run artifact store may preserve detail outside active context, but final synthesis must not reload every artifact indiscriminately.
