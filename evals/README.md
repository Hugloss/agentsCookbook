# Evaluations

Evaluation ownership is repository-level, not OpenCode-directory-level.

The executable fixed benchmark set currently lives in `scripts/run-opencode-benchmarks.js`. It covers full Ping-Pong planning and one-reviewer routing behavior, records sessions, validates runtime call structure, and checks final-answer contracts.

`evals/sharp-skill-discrimination.md` is the behavioral corpus for the narrow specialist skills. Each skill has a positive case and a false-positive control. It is intentionally separate from install/discovery smoke checks: loading a skill proves availability, not discrimination quality.

When adding evaluations:

- test standalone invocation separately from full-flow composition;
- include routing false positives/negatives for short descriptions;
- test specialist skills against both a true defect and a control case;
- require evidence and reject cross-skill drift, not just a plausible-sounding answer;
- test 98k context-pressure behavior with bounded evidence packets;
- test OpenCode and Pi behavioral equivalence rather than only file discovery;
- distinguish 12 installable agents from the exact eight mandatory flow reviewers;
- verify failed/skipped reviewer calls cannot be reported as successes.

The pull-request validation workflow proves canonical source, adapter, authority, artifact, syntax, and smoke contracts. It does not claim that local-model behavioral discrimination has been executed unless an explicit model benchmark run supplies that evidence.

Do not put canonical agent or skill sources under an evaluation or runtime-specific directory.
