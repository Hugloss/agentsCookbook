# Evaluations

Evaluation ownership is repository-level, not OpenCode-directory-level.

The executable fixed benchmark set currently lives in `scripts/run-opencode-benchmarks.js`. It covers full Ping-Pong planning and one-reviewer routing behavior, records sessions, validates runtime call structure, and checks final-answer contracts.

When adding evaluations:

- test standalone invocation separately from full-flow composition;
- include routing false positives/negatives for short descriptions;
- test 98k context-pressure behavior with bounded evidence packets;
- test OpenCode and Pi behavioral equivalence rather than only file discovery;
- distinguish 12 installable agents from the exact eight mandatory flow reviewers;
- verify failed/skipped reviewer calls cannot be reported as successes.

Do not put canonical agent or skill sources under an evaluation or runtime-specific directory.
